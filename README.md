# KX Problem solving exercise

## Problem
We would like you to implement a distributed **Service Assembly** with a gateway component.

## Description
The service assembly will have the following components:
1) **Storage Service** - stores in-memory, dummy data that can be accessed through a REST GET call in JSON format
2) **Gateway Service** - main process that serves data to clients and tracks the availability of the Storage Services (there could be 0 to 3 available) and has the following REST endpoints
    * **/status** - returns the status of each Storage Service
    * **/data** - fetches the dummy data from a Storage Service (eg. with round robin) and returns the data in JSON format

We would like the services to be containerised and run with docker-compose.
The services can be implemented using any programming language.

## Architecture
<img src="https://user-images.githubusercontent.com/90027208/152865747-5c4734dd-c046-4170-ae04-f0ea1448cf89.png" width="300">

## Acceptance criteria
* Please fork this git repository and work inside your own
* Provide a solution for the described problem and give us the instructions necessary to execute it
* We would like to have your solution in form of a Pull Request into the main repository
* _What should the Gateway do if no Storage Services are running?_

## Decision Log
You can find the decision log for this project at the following link: [Decision Log](docs/DECISION_LOG.md).

## Project Structure
### Git
The project will be implemented using a git monorepo structure as follows:

```
main
├── f
│   └── ...
├── storage-service
│   ├── main
│   └── f
│       └── ...
└── gateway-service
│   ├── main
│   └── f
│       └── ...
```

- **main**: Represents the main branch, which contains the core files and documentation for the project.
- **f**: Feature directory that contains various tasks and developments related to the project.
- **storage-service**: Directory for the storage service, containing the main files for the storage service and its associated feature directory.
- **gateway-service**: Directory for the gateway service, containing the main files for the gateway service and its associated feature directory.

This structure allows for a logical and clear arrangement of the projects, facilitating development processes and the management of different functionalities.

Here’s the project structure in English, with the `f` directory removed since the development is happening in a single step:

### Directorys
The project will be implemented using a directory structure as follows:

```
main
├── docs
│   └── <general documentation files>
├── storage-service
│   ├── docs
│   │   └── <storage service documentation files>
│   └── src
│       └── <storage service source files>
└── gateway-service
|   ├── docs
│   |   └── <gateway service documentation files>
|   └── src
|       └── <gateway service source files>
```

- **docs**: A top-level directory for general project documentation.
- **storage-service**: Directory for the storage service, containing:
  - **docs**: Documentation files specific to the storage service.
  - **src**: Source files for the storage service.
- **gateway-service**: Directory for the gateway service, containing:
  - **docs**: Documentation files specific to the gateway service.
  - **src**: Source files for the gateway service.

This structure allows for a logical and clear arrangement of the projects, facilitating development processes and the management of different functionalities.