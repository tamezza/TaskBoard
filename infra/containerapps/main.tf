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
  }
}

provider "azurerm" {
  features {}
}

variable "my_ip" {
  description = "The only public IP address allowed to open the application"
  type        = string
}

variable "location" {
  type    = string
  default = "swedencentral"
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
  location               = azurerm_resource_group.main.location
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

# ---------- Containers ----------

resource "azurerm_container_app_environment" "main" {
  name                = "taskboard-env"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# The API: reachable only from inside the environment.
resource "azurerm_container_app" "api" {
  name                         = "taskboard-api"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  secret {
    name  = "database-url"
    value = local.database_url
  }

  secret {
    name  = "secret-key"
    value = random_password.secret_key.result
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "api"
      image  = "ghcr.io/tamezza/taskboard:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

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
}

# The interface: the only part with a public address, over HTTPS,
# and only for one IP address.
resource "azurerm_container_app" "web" {
  name                         = "taskboard-web"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

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
}

output "url" {
  value = "https://${azurerm_container_app.web.ingress[0].fqdn}"
}
