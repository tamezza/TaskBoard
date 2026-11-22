pipeline {
    agent any

    stages {
        stage('Install') {
            steps {
                sh 'python3 -m venv .venv'
                sh '.venv/bin/pip install -r requirements.txt -r requirements-dev.txt'
            }
        }
        stage('Lint') {
            steps {
                sh '.venv/bin/ruff check .'
            }
        }
        stage('Test') {
            steps {
                sh '.venv/bin/python -m pytest -v'
            }
        }
    }
}
