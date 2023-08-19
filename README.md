# Gcloud configuration

```
gcloud config set project notebookgrader
gcloud auth login

```

Get an auth token:
```
gcloud auth print-identity-token
```



Authenticate: https://cloud.google.com/functions/docs/securing/authenticating

## To run it locally: 

functions-framework --target=grader

## To kill it: 

lsof -i :8080

## Build the zip:

zip Function.zip main.py requirements.txt
