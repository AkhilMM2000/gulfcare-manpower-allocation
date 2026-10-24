# GulfCare — Manpower Allocation

A custom Frappe application for managing manpower requests, employee assignments, staffing availability, conflict validation, and assignment replacements.

Built on **Frappe Framework v16**, with ERPNext CRM and HRMS providing existing business functionality.

## Overview

GulfCare Manpower Allocation helps manage the operational process of fulfilling customer staffing requirements.

The application connects customer-related business processes with manpower requests and employee assignments. It validates assignment data, identifies employee scheduling conflicts, tracks staffing requirements, and supports replacing an active assignment while preserving its history.

## Business Workflow

The intended business workflow is:

1. **Lead** — Record a potential customer.
2. **Opportunity** — Track a potential business deal.
3. **Customer** — Represent the customer organization.
4. **Manpower Request** — Define the staffing requirement, including the number of employees and required dates.
5. **Manpower Assignment** — Assign eligible employees to fulfil the request.

ERPNext provides the existing CRM functionality, while the custom application implements manpower allocation-specific business logic.

## Key Features

### Manpower Requests

- Maintain staffing requirements and service dates.
- Track request status based on staffing fulfilment.
- Calculate staffing shortages against the required workforce.

### Manpower Assignments

- Assign employees to manpower requests.
- Validate assignment dates and employee eligibility.
- Detect overlapping employee assignments.
- Check relevant leave conflicts.
- Enforce assignment status transition rules.
- Validate overstaffing scenarios according to the implemented business rules.

### Assignment Replacement

- Replace an existing active assignment with another employee.
- Require a replacement reason.
- Prevent replacement with the same employee.
- Link the original assignment and its replacement for traceability.
- Cancel the original assignment and activate the replacement through the replacement workflow.
- Use a database savepoint and rollback when the replacement operation fails.

### Access Control

- Use Frappe DocType permissions to control access to custom documents.
- Apply server-side permission checks to sensitive document operations.
- Verify that unauthorized users cannot access the Manpower Assignment DocType through the tested API request.

## Technology Stack

- **Framework:** Frappe Framework v16
- **Business applications:** ERPNext CRM and HRMS
- **Backend:** Python
- **Database:** MariaDB, managed through Frappe
- **Frontend:** Frappe Desk and client-side JavaScript
- **Version control:** Git and GitHub
- **Code quality:** Ruff, ESLint, Prettier, and pre-commit

## Application Architecture

The application uses Frappe's DocType-based architecture.

- **DocTypes** define the structure and configuration of business documents.
- **Python controllers** implement server-side validation and business logic.
- **Document lifecycle hooks** run validation and other logic during document operations.
- **Frappe ORM** provides document and database operations.
- **Client-side JavaScript** provides form interactions, including the assignment replacement action.
- **ERPNext CRM and HRMS** provide existing customer and employee-related functionality.

The custom application extends the existing Frappe ecosystem rather than rebuilding all CRM and HR functionality from scratch.

## Project Structure

The main custom application is located at:


gulfcare_custom/
├── gulfcare_custom/
│   └── manpower_allocation/
│       └── doctype/
│           ├── manpower_request/
│           └── manpower_assignment/
├── hooks.py
├── modules.txt
└── README.md


The repository may contain additional Frappe configuration, DocTypes, tests, and other application files.

## Installation

### Prerequisites

- A working Frappe Bench environment compatible with version 16.
- ERPNext and HRMS installed on the target site.
- Git and the dependencies required by the Frappe environment.

### Install the application

From your Bench directory, run:

```bash
bench get-app https://github.com/AkhilMM2000/gulfcare-manpower-allocation.git --branch version-16
```

Install the application on your site:

```bash
bench --site gulfcare.localhost install-app gulfcare_custom



For an existing development environment where the application is already installed, use the existing Bench and site rather than installing it again.

## Development

Navigate to the application directory:

```bash
cd apps/gulfcare_custom
```

Install the Git pre-commit hooks:

```bash
pre-commit install
```

The repository is configured to use the following code quality tools:

- Ruff
- ESLint
- Prettier
- pyupgrade

Run the project's configured checks using the relevant pre-commit commands and project configuration.

## Verification

Important business scenarios to verify during development include:

- Creating a valid manpower request.
- Assigning an eligible employee.
- Rejecting invalid assignment dates.
- Detecting overlapping assignments and relevant leave conflicts.
- Calculating staffing shortages.
- Rejecting invalid assignment replacements.
- Verifying that the original and replacement assignments remain linked.
- Confirming that unauthorized users are denied access.

## Future Improvements

Potential improvements include:

- Operational role-based permissions for manpower managers and allocation officers.
- More comprehensive automated tests for business rules and authorization.
- Additional reporting and staffing analytics.
- Employee self-service functionality, if required by the business.

## Contributing

Contributions should follow the project's existing code style and quality checks. Install pre-commit hooks before making changes and verify the affected business workflows.

## License

MIT
