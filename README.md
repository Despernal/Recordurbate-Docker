# Recordurbate-Docker [![Docker Image CI](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml/badge.svg)](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml)

## Building
To build this just run the build script

`./build`

## Running
You will need to change paths in

`start` and 
`docker-compose.yml` 

In `docker-compose.yml` you will need to change the the following

```   
      - PATH_TO_RECORDINGS:/app/videos
      - PATH_TO_CONFIGS:/app/configs
```
and in `start` you will need to change the following

```
-v PATH_TO_RECORDINGS:/app/videos/ -v PATH_TO_CONFIGS:/app/configs
```

You can either start it with the start script or do like i do and just use the docker-compose stack to start it

You can run this either way by baking in the configs folder and just not mapping the configs volume out to a real folder on the host.

Or do like i do an just map the provided configs folder into the container and add the appropriate volume mounts.

I have been running this in a container for years sharing it because someone asked.









