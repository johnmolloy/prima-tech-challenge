# Prima Insurance SRE / DevOps Engineer Technical Challenge: Python User API

A REST API built with Flask. Designed to be deployed to an EKS Cluster.

## 🏗️ Architecture Overview

* **Compute:** Containerized Flask API running on Amazon EKS.
* **Networking:** Exposed via an AWS Elastic Load Balancer (ELB)
* **Storage & State:** * User metadata stored in **Amazon DynamoDB** (via IRSA permissions).
  * Profile images/Avatars stored in **Amazon S3** (via IRSA permissions).
* **Elasticity:** Configured with a Horizontal Pod Autoscaler (HPA) to scale between 2 and 10 replicas based on CPU utilization.

## 🚀 DevSecOps CI/CD Pipeline

1. **Code Validation & Security**
   * `pytest`: Executes unit tests for application logic.
   * `Bandit`: Static Application Security Testing (SAST) for Python vulnerabilities.
   * `Hadolint`: Enforces Dockerfile best practices and linting.
2. **Infrastructure Validation**
   * `tfsec`: Scans Terraform plans for cloud misconfigurations (e.g., public buckets, missing encryption).
   * `Infracost`: Automated cloud cost estimation for infrastructure changes. (commented out as it requires an API key)
3. **Artifact Security**
   * `Trivy`: Scans the compiled Docker image for CVEs and OS-level vulnerabilities before pushing to Amazon ECR. Snyk would be preferred, but it's not free :)
4. **Continuous Deployment**
   * Authenticates with AWS via OIDC (or secrets).
   * Pushes the verified image to Elastic Container Registry (ECR).
   * Upgrades the EKS cluster using a custom Helm chart.

## ⚙️ Infrastructure as Code (Terraform)

The base infrastructure is provisioned using Terraform. 

* **State Management:** Remote state stored securely (configure backend in `main.tf`).
* **Resources Managed:** * EKS Cluster & Node Groups
  * VPC, Subnets, and Security Groups
  * DynamoDB Tables and S3 Buckets
  * IAM Roles for Service Accounts (IRSA) mapping AWS permissions directly to Kubernetes Pods.

## ☸️ Kubernetes & Helm

The application is packaged as a Helm chart (`/helm/prima-tech-challenge`), utilizing templated configurations for multi-environment deployments. 

**Key Kubernetes Features Implemented:**
* **Liveness & Readiness Probes:** Ensuring the Load Balancer only routes traffic to healthy pods.
* **Horizontal Pod Autoscaler:** Dynamic scaling based on `metrics-server` CPU targets (75%).
* **Environment Variable Injection:** Dynamic injection of S3 bucket names and DynamoDB tables via Helm `values.yaml` to prevent hardcoded configuration.
* **Least Privilege:** Pods execute under a dedicated ServiceAccount mapped to specific IAM roles.

## 🛠️ Usage & API Endpoints

Once deployed, the Load Balancer URL is automatically retrieved and printed in the GitHub Actions Job Summary. This is clunky and hacky... If this was a proper app we would be adding DNS records for the app and using those instead. Probably wouldn't be using a dedicated load balancer either, for cost reasons. Gateway API or Traefik is probably a better solution. I guess it depends on the organisation's preferred Ingress solution.

Also obviously would use HTTPS and a certificate, rather than http and port 80.

In an ideal world I would also have created separate "dev" and "prod" values files in the helm files. And perhaps even multiple dev environments, and/or UAT environment. Along with extra CI/CD pipeline stages for these.

Likewise, the Terraform files are simplified, with no separate values files for dev and prod etc. And separated out variables file, modules etc. I just chose to use a single main/tf file for simplicity. I also kinda went against the instructions and made myself an EKS cluster. Fully aware of the costs, but my time is worth more really, and this felt like the quickest way to do it to get everything working and to test it. There's a folder nested inside the terrfarom directory, with the TF files I used to provision the EKS cluster. However I did this manually with the Terraform CLI from my local machine rather than via the Github actions pipeline.

**Check System Health:**
```bash
curl -X GET http://<LOAD_BALANCER_URL>/health
```

Retrieve Users:
```bash
curl -X GET http://<LOAD_BALANCER_URL>/users
```

Create a New User (with Image Upload):
```bash
curl -X POST http://<LOAD_BALANCER_URL>/users \
  -F "name=Jane Doe" \
  -F "email=jane@example.com" \
  -F "password=securepassword123" \
  -F "image=@local_profile_pic.png"
```
