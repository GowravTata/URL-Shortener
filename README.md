# URL Shortener Service

A production-inspired URL Shortener built using **FastAPI**, **PostgreSQL**, **Redis**, **Apache Kafka**, **Docker**, and **Terraform**.

The project demonstrates modern backend engineering concepts including authentication, caching, asynchronous event processing, infrastructure provisioning, rate limiting, analytics, and containerized deployment on AWS.

---

# Features

- User Registration & Authentication (JWT)
- URL Shortening
- URL Redirection
- Click Analytics
- Redis Caching
- Rate Limiting
- URL Expiration Support
- Apache Kafka Event Streaming
- Asynchronous Analytics Processing
- Dockerized Deployment
- Infrastructure Provisioning using Terraform
- Swagger / OpenAPI Documentation
- Admin Seed APIs for Demo Data

---

# Technology Stack

| Layer | Technology |
|---------|------------|
| Language | Python |
| Framework | FastAPI |
| Database | PostgreSQL |
| Cache | Redis |
| Event Streaming | Apache Kafka |
| Containerization | Docker |
| Orchestration | Docker Compose |
| Infrastructure | Terraform |
| Cloud | AWS EC2 |

---

# Architecture

The application follows an event-driven architecture.

- FastAPI serves client requests.
- PostgreSQL stores users, URLs, and analytics.
- Redis caches frequently accessed URLs.
- Kafka publishes click events asynchronously.
- Analytics consumers process events without impacting redirect latency.

# Infrastrcuture Architecture 
![InfrastrcutureArchitecture](images/infra_architecture.png)

# System Architecture 
![SystemArchitecture](images/architecture.png)

---

# Request Flow

```

Register User
↓

Login
↓

Create Short URL
↓

Store in PostgreSQL
↓

Cache in Redis
↓

Share URL
↓

User Clicks URL
↓

Lookup Redis

↓

Cache Hit ----------------------→ Redirect

↓

Cache Miss
↓

Read PostgreSQL
↓

Update Redis
↓

Redirect User
↓

Publish Click Event

↓

Kafka

↓

Analytics Consumer

↓

Update Click Statistics

```

---

# Repository Structure

```

url-shortener/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── services/
│   ├── utils/
│   └── ...
│
├── terraform/
│
├── images/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
│
└── .env

```

---

# Prerequisites

Install the following tools before starting.

| Tool | Purpose |
|-------|----------|
| Git | Clone repository |
| Docker | Run containers |
| Docker Compose | Service orchestration |
| Terraform | Infrastructure provisioning |
| AWS Account | Deploy infrastructure |

Verify installations

```bash
git --version

docker --version

docker compose version

terraform version
```

---
## Install Prerequisites

This project provides a single setup script to install all required prerequisites.

### Clone the Repository

```bash
git clone <repository-url>
cd url-shortener
```

### Make the Scripts Executable

```bash
chmod +x scripts/setup.sh
chmod +x scripts/install-awscli.sh
chmod +x scripts/install-terraform.sh
```

### Install AWS CLI & Terraform

Run the setup script:

```bash
./scripts/setup.sh
```

The setup script will automatically:

- Install AWS CLI
- Install Terraform

Once the script completes successfully, verify the installations:

```bash
aws --version
terraform --version
```

# Quick Start

Follow these steps to provision the infrastructure and deploy the application.

## Before You Begin

- Install the following tools:
  - Git
  - Terraform
  - Docker (for local development)
- Create an AWS account with the required permissions.
- Generate an SSH key pair:

```bash
ssh-keygen -t rsa -b 4096 -f my-ec2-key
```

- Copy the generated public key (`my-ec2-key.pub`) to:

```text
terraform/my-ec2-key.pub
```

- Configure your public IP address for SSH access by either:
  - Updating the `my_ip` variable in `terraform/variables.tf`, **or**
  - Passing it during deployment:

---

## Deploy
cd terraform/

terraform init

terraform plan

terraform apply -var="region=us-east-1" -var="my_ip=<REPLACE_MY_IP>" -auto-approve
```

Terraform automatically:

- Provisions the AWS infrastructure.
- Configures the EC2 instance.
- Deploys the application using the EC2 bootstrap script.
- Starts all required Docker containers.

Once the deployment is complete, Terraform outputs the EC2 Public IP.

---

## Verify Deployment

Open Swagger UI:

```text
http://<EC2_PUBLIC_IP>:8000/docs
```

Open Kafka UI:

```text
http://<EC2_PUBLIC_IP>:8080
```

---

## Load Demo Data

Populate the application with sample users, URLs, and click events.

```bash
curl -X POST \
"http://<EC2_PUBLIC_IP>:8000/v1/admin/seed/all"
```

The application is now ready for testing.


# AWS Permissions

For development purposes, the IAM user executing Terraform should have:

```

AmazonEC2FullAccess

```

This keeps the setup simple.

For production environments, replace this with a least-privilege IAM policy.

---

# Verify Deployment

Terraform deploys the application automatically using the EC2 bootstrap script.

After `terraform apply` completes, wait a few minutes for the bootstrap process to finish.

Verify that the application is available by opening:

| Service | URL |
|----------|-----|
| Application | http://<EC2_PUBLIC_IP>:8000 |
| Swagger UI | http://<EC2_PUBLIC_IP>:8000/docs |
| OpenAPI | http://<EC2_PUBLIC_IP>:8000/openapi.json |

If these pages load successfully, the deployment has completed successfully.

## Verify Running Containers

If you suspect the deployment failed, connect to the EC2 instance and verify that the containers are running.

List all running containers.

```bash
docker ps
```

Expected containers include:

```text
url-shortener-api
postgres
redis
kafka
kafka-ui
analytics-consumer
```

If a container is not running, inspect the logs.

```bash
docker compose logs
```

To continuously monitor the logs:

```bash
docker compose logs -f
```


---

# Verify Application

Open Swagger UI.

```text
http://<EC2_PUBLIC_IP>:8000/docs
```

OpenAPI Specification

```text
http://<EC2_PUBLIC_IP>:8000/openapi.json
```

Application Root

```text
http://<EC2_PUBLIC_IP>:8000
```

If Swagger loads successfully, the application is running correctly.

---

## Kafka Verification

Use the following commands to verify that Kafka is running and that your application is publishing events successfully.

### Verify Kafka container

Ensure the Kafka container is running.

```bash
docker ps
```

Expected output should include:

```text
url_shortener_kafka
```

---

### List Kafka topics

Verify that the expected Kafka topics have been created.

```bash
docker exec -it url_shortener_kafka \
/opt/kafka/bin/kafka-topics.sh \
--bootstrap-server localhost:9092 \
--list
```

Expected output:

```text
redirect_queue
```

---

### Describe a topic

View topic details such as partitions and replication factor.

```bash
docker exec -it url_shortener_kafka 
/opt/kafka/bin/kafka-topics.sh \
--bootstrap-server localhost:9092 \
--describe \
--topic redirect_queue
```

---

### Consume messages

Monitor messages published by the application.

```bash
docker exec -it url_shortener_kafka \
/opt/kafka/bin/kafka-console-consumer.sh \
--bootstrap-server localhost:9092 \
--topic redirect_queue \
--from-beginning
```

Keep this terminal open, then access a shortened URL. New events should appear immediately, confirming that Kafka is receiving messages from the application.

---

### Check application logs

If events are not appearing in Kafka, inspect the application logs for producer errors.

```bash
docker logs -f url_shortener_api
```

# Seed Demo Data

The project includes Admin Seed APIs for generating realistic demo data.

These APIs create:

- Test Users
- Shortened URLs
- Click Events

The APIs are intentionally separated so that each step can be executed independently.

---

## Create Users

```http
POST /v1/admin/seed/users
```

Example

```bash
curl -X POST \
"http://<EC2_PUBLIC_IP>:8000/v1/admin/seed/users?count=100"
```

Maximum users allowed:

```text
100
```

---

## Create URLs

> Users must exist before URLs can be created.

```http
POST /v1/admin/seed/urls
```

Example

```bash
curl -X POST \
"http://<EC2_PUBLIC_IP>:8000/v1/admin/seed/urls?count=1000"
```

Maximum URLs allowed:

```text
1000
```

---

## Generate Clicks

> URLs must exist before clicks can be generated.

```http
POST /v1/admin/seed/clicks
```

Example

```bash
curl -X POST \
"http://<EC2_PUBLIC_IP>:8000/v1/admin/seed/clicks?count=1000"
```

Maximum clicks allowed:

```text
1000
```

---

## Seed Everything

Creates users, URLs, and click events in the correct order.

```http
POST /v1/admin/seed/all
```

Example

```bash
curl -X POST \
"http://<EC2_PUBLIC_IP>:8000/v1/admin/seed/all"
```

Default execution:

- 100 Users
- 1000 URLs
- 1000 Click Events

The endpoint internally performs:

```text
Create Users
      ↓
Create URLs
      ↓
Generate Clicks
```

This is the recommended endpoint for populating a fresh environment.

# Verify Event Flow

After seeding data:

1. Open Swagger.
2. Access any generated short URL.
3. The application redirects immediately.
4. A click event is published to Kafka.
5. Analytics Consumer processes the event.
6. Click count is updated asynchronously.

Open Kafka UI to observe the messages in real time.

---

# Redis

Redis is used as a cache for frequently accessed URLs.

Benefits include:

- Faster redirects
- Reduced PostgreSQL queries
- Improved application performance

Redis runs automatically through Docker Compose.

To inspect Redis logs:

```bash
docker compose logs redis
```

---

# PostgreSQL

PostgreSQL stores:

- Users
- Short URLs
- Click Analytics
- URL Metadata

To connect directly:

```bash
docker exec -it url_shortener_postgres psql -U postgres
```

List databases:

```sql
\l
```

List tables:

```sql
\dt
```

---

# Health Verification Checklist

After deployment verify the following:

- Terraform completed successfully.
- EC2 instance is reachable.
- Docker containers are running.
- Swagger UI loads.
- User registration works.
- Login returns JWT.
- URL shortening works.
- Redirect works.
- Kafka receives click events.
- Analytics consumer updates click statistics.
- Redis cache is populated.
- Seed APIs execute successfully.

If all items pass, the deployment is complete.
# REST API Overview

The application exposes REST APIs for authentication, URL management, analytics, and administration.

Interactive API documentation is available through Swagger.

```
http://<EC2_PUBLIC_IP>:8000/docs
```

OpenAPI Schema

```
http://<EC2_PUBLIC_IP>:8000/openapi.json
```

---

# Authentication APIs

## Register User

Creates a new user account.

**Endpoint**

```http
POST /v1/auth/register_user
```

Request

```json
{
    "email": "john.doe@example.com",
    "password": "StrongPassword123"
}
```

Successful Response

```json
{
    "message": "User registered successfully."
}
```

---

## Login

Authenticates the user and returns a JWT access token.

**Endpoint**

```http
POST /v1/auth/login-json
```

Request

```json
{
    "email": "john.doe@example.com",
    "password": "StrongPassword123"
}
```

Response

```json
{
    "access_token": "<jwt-token>",
    "token_type": "bearer"
}
```

---

# URL APIs

## Create Short URL

Creates a shortened URL for an authenticated user.

**Endpoint**

```http
POST /v1/urls
```

Headers

```text
Authorization: Bearer <JWT_TOKEN>
```

Request

```json
{
    "original_url": "https://www.google.com"
}
```

Example Response

```json
{
    "short_code": "Ab12CD",
    "short_url": "http://<EC2_PUBLIC_IP>:8000/Ab12CD"
}
```

---

## Redirect

Redirects the user to the original URL.

**Endpoint**

```http
GET /{short_code}
```

Example

```http
GET /Ab12CD
```

Response

```http
HTTP/1.1 302 Found
Location: https://www.google.com
```

During every redirect the application

- Checks Redis cache
- Falls back to PostgreSQL if needed
- Updates Redis
- Publishes a Kafka event
- Redirects the user immediately

---

# Analytics APIs

Retrieve analytics for a shortened URL.

Example endpoint

```http
GET /v1/analytics/{short_code}
```

Typical response

```json
{
    "short_code": "Ab12CD",
    "total_clicks": 150
}
```

---

# Rate Limiting

The application applies rate limiting to protect public APIs.

Benefits

- Prevents abuse
- Prevents excessive URL creation
- Protects backend services
- Demonstrates production-ready API design

---

# Project Structure

```
url-shortener/
│
├── app/
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│
├── images/
│
├── terraform/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
│
└── .env
```

---

# Troubleshooting

## Docker Permission Denied

```text
permission denied while trying to connect to Docker daemon
```

Solution

```bash
sudo usermod -aG docker ubuntu

newgrp docker
```

Logout and login again if required.

---

## PostgreSQL Connection Timeout

Verify

- PostgreSQL container is running.
- Security Group allows the required port.
- Docker network is healthy.

Useful commands

```bash
docker compose logs postgres

docker ps
```

---

## Kafka Issues

Check Kafka logs.

```bash
docker compose logs kafka
```

Verify Kafka UI.

```
http://<EC2_PUBLIC_IP>:8080
```

Ensure topics are created.

---

## Redis Issues

View Redis logs.

```bash
docker compose logs redis
```

Restart Redis.

```bash
docker compose restart redis
```

---

## Application Not Starting

View logs.

```bash
docker compose logs api
```

Rebuild containers.

```bash
docker compose up -d --build
```

---

## Terraform Issues

Reinitialize Terraform.

```bash
terraform init
```

View current infrastructure.

```bash
terraform state list
```

Destroy infrastructure.

```bash
terraform destroy
```

Provision again.

```bash
terraform apply
```

---

# Useful Docker Commands

Start all services

```bash
docker compose up -d
```

Rebuild containers

```bash
docker compose up -d --build
```

Stop services

```bash
docker compose down
```

Restart services

```bash
docker compose restart
```

View logs

```bash
docker compose logs -f
```

List containers

```bash
docker ps
```

List images

```bash
docker images
```

---

# Useful Terraform Commands

Initialize

```bash
terraform init
```

Plan

```bash
terraform plan
```

Apply

```bash
terraform apply
```

Destroy

```bash
terraform destroy
```

Show Outputs

```bash
terraform output
```

---


---

# Learning Objectives

This project demonstrates practical experience with

- REST API Design
- Authentication using JWT
- FastAPI
- PostgreSQL
- Redis Caching
- Apache Kafka
- Event-Driven Architecture
- Rate Limiting
- Docker & Docker Compose
- Infrastructure as Code using Terraform
- AWS EC2 Deployment
- Production-style Backend Design

---

# License

MIT License

Feel free to use this project for learning, experimentation, and personal development.
# Deployment Checklist

Use this checklist whenever deploying the project to a new environment.

## Infrastructure

- [ ] AWS credentials configured
- [ ] Terraform initialized
- [ ] Terraform plan reviewed
- [ ] Terraform apply completed
- [ ] EC2 instance created
- [ ] Security Group configured
- [ ] Elastic IP (if applicable) associated

---

## Application

- [ ] Repository cloned
- [ ] Environment variables configured
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] Application started
- [ ] All containers healthy

---

## Verification

- [ ] Swagger UI accessible
- [ ] PostgreSQL container running
- [ ] Redis container running
- [ ] Kafka container running

---

## Demo Data

- [ ] Users seeded
- [ ] URLs seeded
- [ ] Clicks generated

---

## Functional Testing

- [ ] Register user
- [ ] Login
- [ ] Create short URL
- [ ] Redirect works
- [ ] Click event published
- [ ] Analytics updated

Deployment is complete once every item above has been verified.

---
# Environment Variables

The application relies on the following environment variables.

| Variable | Description |
|-----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| SECRET_KEY | JWT signing secret |
| ACCESS_TOKEN_EXPIRE_MINUTES | JWT expiration time |
| REDIS_HOST | Redis hostname |
| REDIS_PORT | Redis port |
| KAFKA_BOOTSTRAP_SERVERS | Kafka broker |
| API_BASE_URL | Base URL used by Admin Seed APIs |

Example

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/url_shortener

SECRET_KEY=change-me

ACCESS_TOKEN_EXPIRE_MINUTES=60

REDIS_HOST=redis
REDIS_PORT=6379

KAFKA_BOOTSTRAP_SERVERS=kafka:9092

API_BASE_URL=http://localhost:8000
```

---
# Notes for Future Me

If you're returning to this project after months or years, remember the following.

### Infrastructure

Infrastructure is provisioned using Terraform.

```bash
cd terraform

terraform init

terraform apply
```

---

### Application

Start everything using Docker Compose.

```bash
docker compose up -d --build
```

---

### Demo Data

Populate the database.

```bash
POST /v1/admin/seed/all
```

or

```bash
curl -X POST \
"http://<HOST>:8000/v1/admin/seed/all"
```

---

### Useful URLs

Swagger

```
http://<HOST>:8000/docs
```

Kafka UI

```
http://<HOST>:8080
```

Application

```
http://<HOST>:8000
```

---

### Common Issues

Docker Permission

```bash
sudo usermod -aG docker ubuntu

newgrp docker
```

---

Container Status

```bash
docker ps
```

---

Application Logs

```bash
docker compose logs -f
```

---

Terraform Outputs

```bash
terraform output
```

---

Destroy Everything

```bash
terraform destroy
```

---

Rebuild Application

```bash
docker compose down

docker compose up -d --build
```

---

If the infrastructure deploys successfully, the containers are healthy, and the seed API completes successfully, the application should be fully operational.

Good luck!
