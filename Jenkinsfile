pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }

  parameters {
    booleanParam(
      name: 'NO_CACHE',
      defaultValue: false,
      description: 'Rebuild Docker images without cache'
    )
  }

  environment {
    COMPOSE_PROJECT_NAME = 'ai-coding-workspace'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Docker Info') {
      steps {
        script {
          if (isUnix()) {
            sh 'docker --version'
            sh 'docker compose version'
          } else {
            powershell 'docker --version'
            powershell 'docker compose version'
          }
        }
      }
    }

    stage('Build & Deploy') {
      steps {
        script {
          if (isUnix()) {
            sh '''
              chmod +x deploy/jenkins-deploy.sh
              ./deploy/jenkins-deploy.sh
            '''
          } else {
            powershell """
              \$ErrorActionPreference = 'Stop'
              \$noCache = '${params.NO_CACHE}'
              if (\$noCache -eq 'true') {
                ./deploy/jenkins-deploy.ps1 -NoCache
              } else {
                ./deploy/jenkins-deploy.ps1
              }
            """
          }
        }
      }
    }
  }

  post {
    success {
      echo 'Deploy finished. Frontend: http://localhost/ Backend: http://localhost:8000/api'
    }
    failure {
      echo 'Deploy failed. Check Docker, .env, port usage, and Jenkins workspace logs.'
    }
  }
}
