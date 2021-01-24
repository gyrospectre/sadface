# Splunk Automated Deployment Function Avoids Content Errors (SADFACE)
SADFACE allows you to programatically deploy your Splunk content from code.

[![Via Giphy](https://media.giphy.com/media/ycdVnD1sAcWkw/giphy.gif)](https://giphy.com/embed/ycdVnD1sAcWkw)

## Why?
In multi-user environments, keeping content consistent in Splunk is hard. Searches can be changed, deleted and configured incorrectly. When you rely on saved searches as a key part of your early warning system (be it for Cybersecurity, operations, or anything else), getting it wrong can be a big deal. SADFACE attempts to help with this.

## What does it do?
SADFACE consists of a single lamdba function, that loads config files and deploys them to a Splunk instance. It is intended to run every day under schedule, or invoked from a build pipeline when config changes. This means you can define your alerts in code, and every day they'll be synced with Splunk. If anyone messes with the content through the Splunk UI, they'll be reset in the next run, keeping everything consistent. You can also set the config to remove content from Splunk if it does not exist in the repo, in order to keep content an exact mirror of the source of truth.

## Limitations
Currently, SADFACE only supports deployment of saved searches as alerts.
It only supports three actions:
- OpsGenie
- Send to email
- Add to triggered alerts

More stuff will come later if I have time and/or there is interest (or code contributions from the helpful public!).

## Invoking from command line
You can run SADFACE from the command line, without any AWS components. Handy if you just want to run SADFACE locally to see how it works:

First, clone the repo, and install deps:
```
git clone https://github.com/gyrospectre/sadface
cd sadface
pip install -r src/requirements.txt
```
Next, configure your Splunk content in the `content` directory (see below for syntax).

Finally, pop your Splunk username and password into environment variables.
```
export SPLUNK_USER=admin
export SPLUNK_PASS=SupersecretPass!
```
You can now run SADFACE from the commend line.
```
python src/sadface.py deploy
```
Check out the full usage for details on various logging options.
```
python src/sadface.py --help
```

## Running in AWS
Running locally is not ideal, nor is storing passwords in env variables. For production use, it's recommended to run in AWS. This is easy! From the main SADFACE directory, and with valid AWS creds in your session:
```
pip install -r requirements-dev.txt
sam build --use-container
sam deploy --guided
```
This will spin up a Cloudformation stack consisting of a single lambda function, which will run a deploy every day. Example run:
```
$ sam build --use-container
Starting Build inside a container
Building codeuri: src runtime: python3.8 metadata: {} functions: ['Function']

Fetching amazon/aws-sam-cli-build-image-python3.8 Docker container image......
Mounting /sadface/src as /tmp/samcli/source:ro,delegated inside runtime container

Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml

Commands you can use next
=========================
[*] Invoke Function: sam local invoke
[*] Deploy: sam deploy --guided
    
Running PythonPipBuilder:ResolveDependencies
Running PythonPipBuilder:CopySource
$ sam deploy --guided

Configuring SAM deploy
======================

	Looking for config file [samconfig.toml] :  Not found

	Setting default arguments for 'sam deploy'
	=========================================
	Stack Name [sam-app]: sadface
	AWS Region [us-east-1]: ap-southeast-2
	#Shows you resources changes to be deployed and require a 'Y' to initiate deploy
	Confirm changes before deploy [y/N]: N
	#SAM needs permission to be able to create roles to connect to the resources in your template
	Allow SAM CLI IAM role creation [Y/n]: Y
	Save arguments to configuration file [Y/n]: Y
	SAM configuration file [samconfig.toml]: 
	SAM configuration environment [default]: 

	Looking for resources needed for deployment: Found!
  <snip>
  Successfully created/updated stack - sadface in ap-southeast-2
$
```
You'll need to pop your Splunk creds into AWS secrets manager, by default in a secret called `splunk` and with content like this:
```
{
    'user': 'admin',
    'pass': 'SupersecretPass!'
}
```
You can change the secret name or the key names in the SADFACE config file if you need to. If you need a (reasonably) least privilage IAM role for this deployment, check out `sadface-deploy.iam` in the main directory. Update the placeholders in this file with your AWS account ID before using!

## Invoking from AWS
If you'd like to manually run SADFACE from AWS, invoke the deployed lambda, as you would normally, from the Lambda console in the UI. (See step 4 from here if you need help: https://aws.amazon.com/getting-started/hands-on/run-serverless-code/)

Your test event should just beblank (`{}`), or you can add a debug flag for verbose logging.
```
{
  'debug': true
}
```

## SADFACE Configuration
The behaviour of SADFACE is controlled by a file `src/config.yaml`. It's commented, so should be pretty easy to work out what does what.

### Section: General
**warn_unmanaged**

Produce a warning at the end of each run, listing any searches not managed by code.

Type: *boolean*

Valid values: *true*, *false*

**remove_unmanaged**

List of apps for which SADFACE should remove any non-managed searches. If an app is not listed here, these searches will be left as is.

Type: *list*

Valid values: Any Splunk app installed on the target instance.

### Section: Splunk
**host**
The target Splunk instance's hostname or IP address.

Type: *string*

Valid values: A hostname or IP address.

**port**
The port number of target Splunk instance's REST API.

Type: *int*

Valid values: Port number. Usually 8089.

**verify**
Whether to ignore any HTTPS errors when accessing the Splunk REST API.

Type: *boolean*

Valid values: *true*, *false*

#### Sub Section: secrets
**order**

List of locations where the Splunk secrets may be stored. Values specified here must have a corresponding stanza of this name in this section.

Type: *list*

Valid values: *env_vars*, *secrets_manager*

**env_vars**

*username*:
The name of the environment variable that holds the Splunk username to use for REST calls.

*password*:
The name of the environment variable that holds the Splunk password to use for REST calls.

**secrets_manager**

*secret*:
The name of the AWS Secrets Manager secret that holds connection details.

*username*:
The name of the key in the Secrets Manager secret that holds the Splunk username to use for REST calls.

*password*:
The name of the key in the Secrets Manager secret that holds the Splunk password to use for REST calls.

## Splunk Content Configuration
The `content` directory holds all the content to be deployed. Inside this directory, a sub-directory should be created for each Splunk app you wish to manage. Within the app directory, create a sub-directory that holds the type of content it contains. At present, only saved searches are supported, in a directory called `searches`. Take a look at the example search, which is deployed to the `splunk_enterprise_on_docker` app.

```
content
   |
   search
      |
      searches
        - search1.yaml
        - search2.yaml
```

These yaml files have the following format. Check out the example search (which has all values set), and refer to the full schema in `src/schemas/search.json` for full details on every value that is possible.
```
Test Search:
  description: Alert if Dad jokes are detected.
  disabled: false
  lookback: -1h
  search: >-
    index=main
    | stats count by index
  cron_schedule: '*/5 * * * *'
  severity: Critical
  actions:
    - Add to Triggered Alerts
  cyber:
    technique: T1000
    tactic: Impact
```
Note that the `cyber` section is optional, but if you're managing threat detection rules with SADFACE, this section will add `evals` to your search to set variables to map your detection to Mitre ATT&CK tactics and techniques. In the above example, the search SPL deployed to Splunk will be expanded to:
```
index=main | stats count by index | eval technique="T1000" | eval tactic="Impact" | eval Detection="Test Search" | eval Severity="Critical"
```

## Validation
The command line invokation of SADFACE also supports validation of the Splunk configuration files (against the schema in the `src/schemas` directory). This is intended to run as a test attached to pull requests in the repository, to catch errors early. To run:
```
python src/sadface.py validate
```

## Testing
If you need to test something quickly, I've included a handy dandy script called `run-splunk.sh` in the main directory. As long as you have docker installed, this script will prompt you for a password and then run up a local Splunk instance for you to test with.

```
$ ./run-splunk.sh 
Specify a Splunk admin password:
9f87a911147e04322b1fb37134db8e851cbf3862e30cbbc1ff2223a6703cc24f
$ docker ps
9f87a911147e   splunk/splunk:latest   "/sbin/entrypoint.sh…"   4 seconds ago   Up 3 seconds (health: starting)   8065/tcp, 0.0.0.0:8000->8000/tcp, 8088/tcp, 8191/tcp, 9887/tcp, 0.0.0.0:8089->8089/tcp, 9997/tcp   splunk
```