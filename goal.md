# Project Context & Goal

I am preparing a portfolio project for a **Senior Test Engineer - Cybersecurity** role at Siemens Mobility (focused on cloud-native SaaS platforms). To demonstrate my expertise in modern security testing—including SAST (Static Application Security Testing), DAST (Dynamic Application Security Testing), and best practices aligned with the OWASP Top 10—I will build a proof-of-concept application alongside a highly modular, automated test infrastructure toolkit.

**Objective:**  
Develop a fully Dockerized, cloud-ready e-commerce backoffice SaaS application with a Python RESTful API backend (using FastAPI or Flask) and a Python-based frontend (Jinja2 or Streamlit, structured for easy Android WebApp wrapping). The project will be evolved across 10 structured iterations, each introducing (on purpose) one of the OWASP Top 10 risks (from #10 to #1). For every iteration:  
- The targeted risk is introduced (by design) in the new or extended application feature.  
- Automated tests specific to that risk are implemented.  
- A markdown advisory is generated based on the detection.  
- The risk is then remediated, and the branch is tagged and merged.

All code is versioned in a private GitHub repo (`https://github.com/barbashaman/cybersecurity-prep-project.git`) with CI/CD gates (GitHub Actions) from day one, integrating SAST (Bandit/Semgrep), DAST (OWASP ZAP), and fully repeatable pipelines.

---

## 1. Architecture & Tech Stack

**Backend:** Python RESTful API (FastAPI/Flask)  
**Frontend:** Python-based UI (Jinja2 or Streamlit), Android-WebApp-friendly  
**Database:** Dockerized (e.g., PostgreSQL, or SQLite for portability), ORM-managed  
**Infrastructure:** Fully Dockerized, orchestrated via `docker-compose`—Infrastructure as Code (IaC)

**Testing Toolkit (`tests/`):**  
- **Internal, Agnostic Framework:** Highly modular test toolkit engineered for universal reuse and dependency-injected context (supporting both black-box and white-box testing).
- **BDD Approach:** All test cases authored in Gherkin for clear, agile-friendly communication.
- **Tooling:**
    - **Robot Framework:** For E2E, web functional, and security tests.
    - **Playwright (Python):** For API integration and functional testing.
- **Reporting:** All test executions output detailed HTML-based reports with comprehensive test descriptions and a success-rate graph summary.

---

## 2. Application Functional Specification (E-Commerce SaaS)

**Multi-Tenant, Proof-of-Concept Features:**  
- **Admin**: Full backoffice and store configuration authority.
- **Store Owner (Tenant):** Personalized access, inventory and order management for their respective store only. Strict access isolation (only owner + admin).
- **Customer:** Access to items/orders of their specific store only. Enforced via backend (prevents insecure direct access, e.g., via URL manipulation).
- **Delivery Manager:** Can only see/update anonymous order statuses (no access to PII; uses only unidentifiable UUIDs).

*No real purchases are processed. A mock purchase module supplies unlimited, fake customer credits for demonstration/E2E simulation.*

**Baseline Database Seeding:**  
All pipelines/tests launch against a pre-seeded app state:  
- 1 Admin, 2 Store Owners, 2 Customers, 1 Delivery Manager  
- Two stores, 10+ products per store, and several staged (to-be-delivered/in-transit) orders (to facilitate all access states and security checks).

---

## 3. Security Iteration Lifecycle & Branching

- **Each OWASP risk/feature delivered via:**
    - Dedicated branch: `iter-<serial>-owasp-<risk>-<risk_name>` (e.g., `iter-01-owasp-10-ssrf`)
    - Step-wise delivery: feature/vulnerability (Red), detection/test/advisory (Red), remediation (Green), validation, tag/merge.
- **Each iteration:**
    1. Branch from `main`
    2. Deliver new feature *with* the specific OWASP risk intentionally included.
    3. Implement tests/DAST/SAST that should fail (detect risk)
    4. Generate a markdown advisory reporting/explaining the flaw
    5. Refactor/code fix to remediate
    6. Confirm green pipelines & merge

---

## 4. DevSecOps Pipeline & Scripting

- **Pipelines (CI/CD):**  
    - All builds/test on ephemeral, seeded databases
    - SAST: Bandit/Semgrep
    - DAST: OWASP ZAP
- **Bash Scripts:**  
    - `run_app.sh` — fail-safe app startup (auto-detects/cleans/handles Docker edge-cases).
    - `run_tests_<type>.sh` — per-type test runner script.
    - `run_all_tests.sh` — full suite runner.
    - *All scripts dynamically check if the correct app version is running before test execution.*

---

## 5. Engineering & Documentation Standards

- Full OOP, strict SOLID adherence, clean architecture, and explicit, descriptive naming conventions (no magic strings/abbreviations).
- Each technical decision, architecture, and branch must be documented.
- *Documentation convention*:  
    ```
    Document Name: <Name Document of the>
    Covered Elements: <Description covered elements/features of the>
    Creation Date: dd/MM/yyyy-HH:mm:ss.fff
    ```
---

## 6. Project Roadmap

**Phase 1: Foundation & DevSecOps Bootstrap**
- Git init, connect to GitHub repo
- Scaffold API, FE, ORM/seeder, Dockerfiles, `tests/` structure, and initial pipelines/scripts

**Phase 2: The OWASP Countdown (Development Iterations)**
- 10 iterations: feature + risk injection + test + advisory + fix (from OWASP #10 → #1)

**Phase 3: Golden Master**
- All vulnerabilities remediated, all tests pass (ZAP, Bandit/Semgrep, Robot, Playwright)

---

## First Action

Please acknowledge this plan, summarize your understanding of the architecture, Security Iteration Lifecycle, engineering constraints (SOLID, Clean Architecture), and the advisory/reporting process.  
Then, provide initial terminal commands for Phase 1 bootstrapping, including directory structure, Git init, virtual env creation, Docker scaffolding, and GitHub Actions yaml setup.  
**Do not write any application code yet.**
