# DELIBERATELY VULNERABLE — DO NOT RUN OUTSIDE A SANDBOX

The code in this directory exists to be broken. It is the
"before" half of Chapter 23 and is never imported by the
server.

Every file here contains at least one of:

- command injection through a shell string
- server-side request forgery through a URL parameter
- unbounded execution with no timeout

Nothing here is a supported configuration. If you find this
directory in a deployment, that is the finding.
