terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      # A deleted vault normally stays recoverable for days and keeps its
      # name reserved. This deployment is temporary: remove it completely.
      purge_soft_delete_on_destroy = true
    }
  }
}

# Who is running Terraform (you, through "az login")
data "azurerm_client_config" "current" {}

variable "my_ip" {
  description = "The only public IP address allowed to open the application"
  type        = string
}

variable "location" {
  type    = string
  default = "swedencentral"
}

variable "db_location" {
  description = "Region of the database, if the main region has no capacity"
  type        = string
  default     = "swedencentral"
}

variable "github_subject" {
  description = "GitHub token subject, for access to the container registry: this repository, in its azure environment"
  type        = string
  default     = "repo:tamezza@130645657/TaskBoard@1467089786:environment:azure"
}

variable "image_tag" {
  description = "Tag of the two images to deploy: latest, or a commit SHA"
  type        = string
  default     = "latest"
}

# Names of database servers are unique across all of Azure,
# so a few random characters are added to ours.
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

# Secrets are generated here, never typed and never written in the repository.
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "taskboard-app-rg"
  location = var.location
  tags     = { project = "taskboard" }
}

# ---------- Database: managed PostgreSQL ----------

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "taskboard-db-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = var.db_location
  version                = "17"
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768
  administrator_login    = "taskboard"
  administrator_password = random_password.db.result

  # Azure picks the availability zone; do not treat that as a change.
  lifecycle {
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "taskboard"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# The special range 0.0.0.0 - 0.0.0.0 means "services running inside Azure".
# It does not open the database to the whole internet.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

locals {
  database_url = join("", [
    "postgresql+psycopg://taskboard:${random_password.db.result}",
    "@${azurerm_postgresql_flexible_server.main.fqdn}:5432/taskboard",
    "?sslmode=require",
  ])
}

# ---------- Secrets: Key Vault and a managed identity ----------

resource "azurerm_key_vault" "main" {
  name                       = "taskboard-kv-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
}

# An identity for the API: an account for a program, with no password to
# store anywhere. Azure proves who the container is.
resource "azurerm_user_assigned_identity" "api" {
  name                = "taskboard-api-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# Least privilege, twice:
# you may write secrets in this vault (to create them)...
resource "azurerm_role_assignment" "me_writes_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ...and the API may only read them.
resource "azurerm_role_assignment" "api_reads_secrets" {
  scope                            = azurerm_key_vault.main.id
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = azurerm_user_assigned_identity.api.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

# Azure takes up to a minute or two to apply new permissions everywhere.
resource "time_sleep" "permissions" {
  create_duration = "90s"

  depends_on = [
    azurerm_role_assignment.me_writes_secrets,
    azurerm_role_assignment.api_reads_secrets,
  ]
}

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  value        = local.database_url
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [time_sleep.permissions]
}

resource "azurerm_key_vault_secret" "secret_key" {
  name         = "secret-key"
  value        = random_password.secret_key.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [time_sleep.permissions]
}

# ---------- Containers ----------

# ---------- Deployment from GitHub, with no stored password ----------

# A second identity, separate from the API's: this one is for the pipeline.
resource "azurerm_user_assigned_identity" "deployer" {
  name                = "taskboard-deployer-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# Accept a token issued by GitHub for Azure.
resource "azurerm_federated_identity_credential" "github" {
  name                      = "github-actions"
  user_assigned_identity_id = azurerm_user_assigned_identity.deployer.id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = var.github_subject
}

# What the pipeline may do: manage this resource group.
resource "azurerm_role_assignment" "deployer" {
  scope                            = azurerm_resource_group.main.id
  role_definition_name             = "Contributor"
  principal_id                     = azurerm_user_assigned_identity.deployer.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_container_app_environment" "main" {
  name                = "taskboard-env"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  # Pay-per-use mode. Azure sets it by default; declaring it keeps
  # "terraform plan" from reporting a difference that is not one.
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

# The API: reachable only from inside the environment.
resource "azurerm_container_app" "api" {
  name                         = "taskboard-api"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  # The values are no longer here: only where to find them in the vault,
  # and which identity to present when asking.
  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.database_url.versionless_id
    identity            = azurerm_user_assigned_identity.api.id
  }

  secret {
    name                = "secret-key"
    key_vault_secret_id = azurerm_key_vault_secret.secret_key.versionless_id
    identity            = azurerm_user_assigned_identity.api.id
  }

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "api"
      image  = "ghcr.io/tamezza/taskboard:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      # The image's default command migrates the database, then starts the
      # server. Here the migration is a separate job, so the API only serves.
      # That is what makes several replicas safe.
      command = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "SECRET_KEY"
        secret_name = "secret-key"
      }
    }
  }

  ingress {
    external_enabled           = false
    target_port                = 8000
    allow_insecure_connections = true

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_postgresql_flexible_server_database.main,
    azurerm_postgresql_flexible_server_firewall_rule.azure_services,
  ]

  # Terraform creates the app; the pipeline decides which version runs.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# The migration: a job, not a service. It runs once when started, applies
# the schema changes, and stops. It uses the same image and the same secret
# as the API, so it migrates with exactly the code being released.
resource "azurerm_container_app_job" "migrate" {
  name                         = "taskboard-migrate"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  container_app_environment_id = azurerm_container_app_environment.main.id
  workload_profile_name        = "Consumption"

  replica_timeout_in_seconds = 300
  replica_retry_limit        = 1

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.database_url.versionless_id
    identity            = azurerm_user_assigned_identity.api.id
  }

  template {
    container {
      name    = "migrate"
      image   = "ghcr.io/tamezza/taskboard:${var.image_tag}"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["alembic", "upgrade", "head"]

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
    }
  }

  depends_on = [
    azurerm_postgresql_flexible_server_database.main,
    azurerm_postgresql_flexible_server_firewall_rule.azure_services,
  ]

  # Terraform creates the app; the pipeline decides which version runs.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

# The interface: the only part with a public address, over HTTPS,
# and only for one IP address.
resource "azurerm_container_app" "web" {
  name                         = "taskboard-web"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "web"
      image  = "ghcr.io/tamezza/taskboard-web:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      # Inside the environment, an app is reachable by its name.
      env {
        name  = "API_URL"
        value = "http://${azurerm_container_app.api.name}"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080

    ip_security_restriction {
      name             = "only-me"
      action           = "Allow"
      ip_address_range = "${var.my_ip}/32"
    }

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }


  # Terraform creates the app; the pipeline decides which version runs.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}

output "url" {
  value = "https://${azurerm_container_app.web.ingress[0].fqdn}"
}

output "migrate_command" {
  description = "Run this after every apply that changes the image"
  value       = "az containerapp job start --name ${azurerm_container_app_job.migrate.name} --resource-group ${azurerm_resource_group.main.name}"
}


output "github_settings" {
  description = "Values to store in the GitHub environment named azure"
  value = {
    AZURE_CLIENT_ID       = azurerm_user_assigned_identity.deployer.client_id
    AZURE_TENANT_ID       = data.azurerm_client_config.current.tenant_id
    AZURE_SUBSCRIPTION_ID = data.azurerm_client_config.current.subscription_id
  }
}