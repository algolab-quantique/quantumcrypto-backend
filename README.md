# QuantumCrypto Backend

Welcome to the backend repository of QuantumCrypto! This project serves as the backend for the QuantumCrypto web application, which gamifies quantum key distribution (QKD) protocols for quantum computing education. The backend is built with Django REST Framework.

## Introduction

QuantumCrypto is an open-source web framework designed to provide an intuitive interface for experimenting with QKD protocols. By gamifying QKD protocols, users can simulate and explore quantum cryptography concepts in real-time interactions.

## Running Locally

To run the QuantumCrypto backend locally, follow these steps:

1. Clone this repository to your local machine:

2. Navigate to the project directory:
   ```
   cd quantumcrypto-backend
   ```

3. Set up a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```

4. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

6. Run migrations to create the database schema:
   ```
   python manage.py migrate --run-syncdb 
   ```

7. Start the development server:
   ```
   python manage.py runserver
   ```

8. Open your browser and visit `http://localhost:8000` to access the QuantumCrypto backend API.

**Note:** Make sure to also run the frontend server locally for full functionality. You can find the frontend repository [here](https://github.com/algolab-quantique/quantumcrypto-frontend).

## Contributing

We welcome contributions from the community to help improve QuantumCrypto. If you'd like to contribute, please follow these guidelines:

1. Fork the repository and create a new branch for your feature or fix.

2. Make your changes and ensure that the code follows the project's coding standards.

3. Write tests for your changes to maintain code quality.

4. Submit a pull request with a clear description of your changes and their purpose.

5. Your pull request will be reviewed by the project maintainers, and any necessary feedback will be provided.

Thank you for contributing to QuantumCrypto! We appreciate your support in making quantum computing education accessible and engaging for all.
