param(
  [string]$JenkinsUrl = "http://localhost:8080",
  [string]$JobName = "AI-Coding-Workspace",
  [string]$RepoUrl = "https://github.com/HarleenDance/AI-Coding-Workspace.git",
  [string]$Branch = "main",
  [string]$ScriptPath = "Jenkinsfile",
  [string]$PollSchedule = "H/2 * * * *",
  [string]$Username = "chenzemian",
  [string]$ApiToken = "112d6dd20984e37c247625bf097fe6223f"
)

$ErrorActionPreference = "Stop"

function ConvertTo-XmlEscaped([string]$Value) {
  return [System.Security.SecurityElement]::Escape($Value)
}

function New-Headers {
  $headers = @{}
  if ($Username -and $ApiToken) {
    $pair = "{0}:{1}" -f $Username, $ApiToken
    $encoded = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
    $headers["Authorization"] = "Basic $encoded"
  }

  try {
    $crumb = Invoke-RestMethod -Uri "$JenkinsUrl/crumbIssuer/api/json" -Headers $headers -Method Get
    $headers[$crumb.crumbRequestField] = $crumb.crumb
  } catch {
    Write-Host "Crumb issuer is unavailable or auth is disabled; continue without crumb." -ForegroundColor Yellow
  }

  return $headers
}

$safeRepo = ConvertTo-XmlEscaped $RepoUrl
$safeBranch = ConvertTo-XmlEscaped "*/$Branch"
$safeScript = ConvertTo-XmlEscaped $ScriptPath
$safeSchedule = ConvertTo-XmlEscaped $PollSchedule

$configXml = @"
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <actions/>
  <description>AI Coding Workspace auto deploy pipeline</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps">
    <scm class="hudson.plugins.git.GitSCM" plugin="git">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>$safeRepo</url>
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>$safeBranch</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="empty-list"/>
      <extensions/>
    </scm>
    <scriptPath>$safeScript</scriptPath>
    <lightweight>true</lightweight>
  </definition>
  <triggers>
    <hudson.triggers.SCMTrigger>
      <spec>$safeSchedule</spec>
      <ignorePostCommitHooks>false</ignorePostCommitHooks>
    </hudson.triggers.SCMTrigger>
  </triggers>
  <disabled>false</disabled>
</flow-definition>
"@

$headers = New-Headers
$headers["Content-Type"] = "application/xml"

$encodedJobName = [uri]::EscapeDataString($JobName)
$jobUrl = "$JenkinsUrl/job/$encodedJobName"

try {
  Invoke-WebRequest -Uri "$jobUrl/api/json" -Headers $headers -UseBasicParsing -Method Get | Out-Null
  Write-Host "Job exists, updating config: $JobName" -ForegroundColor Yellow
  Invoke-WebRequest -Uri "$jobUrl/config.xml" -Headers $headers -UseBasicParsing -Method Post -Body $configXml | Out-Null
} catch {
  Write-Host "Creating job: $JobName" -ForegroundColor Cyan
  Invoke-WebRequest -Uri "$JenkinsUrl/createItem?name=$encodedJobName" -Headers $headers -UseBasicParsing -Method Post -Body $configXml | Out-Null
}

Write-Host "Jenkins job is ready: $JenkinsUrl/job/$encodedJobName" -ForegroundColor Green
Write-Host "It will poll GitHub with schedule: $PollSchedule" -ForegroundColor Green
