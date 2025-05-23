# Live Testing Instructions for Database Integration

## Prerequisites

Before testing with live LLM calls, ensure you have:

1. Set up your API keys in the `.env` file in the project root:
```
GOOGLE_API_KEY=your_real_google_api_key_here
```

2. Installed all required dependencies:
```bash
pip install -e .
```

## Testing Flask SQLAlchemy Integration

To test the Flask API with SQLAlchemy integration using a live LLM call, use this command:

```bash
python -m devspark.cli init --name FlaskDB --template python_flask_api --ai --desc "Flask API with SQLAlchemy integration for the 'task' resource. Include a Task model with 'title' (String, required), 'description' (Text), 'completed' (Boolean), and 'due_date' (DateTime) fields. Add Flask-Migrate for database migrations." --api-prefix "api/v1" --resource "task" --author "Test Author" --python-version "3.9"
```

This command will:
- Create a new Flask API project named "FlaskDB"
- Use the live LLM to generate SQLAlchemy database integration
- Create a Task model with the specified fields
- Set up Flask-Migrate for database migrations
- Configure the service layer to use SQLAlchemy

## Testing Node.js MongoDB Integration

To test the Node.js Express API with MongoDB integration using a live LLM call, use this command:

```bash
python -m devspark.cli init --name MongoDB --template nodejs_express_api --ai --desc "Node.js Express API with MongoDB integration. Add Mongoose models for the 'user' resource, including fields for 'username' (String, required), 'email' (String, required, unique), 'password' (String, required), and 'createdAt' (Date, default to now). Update the service layer to use MongoDB for CRUD operations." --api-base-path "/api/v1" --main-resource "user" --author "Test Author" --node-version "18.x"
```

This command will:
- Create a new Node.js Express API project named "MongoDB"
- Use the live LLM to generate MongoDB/Mongoose integration
- Create a User model with the specified fields
- Configure the database connection
- Update the service layer to use MongoDB

## Analyzing Results

After running either test, analyze the generated project structure:

1. Verify dependencies:
   - For Flask: Check requirements.txt for flask-sqlalchemy, flask-migrate
   - For Node.js: Check package.json for mongoose

2. Examine model definitions:
   - For Flask: Check app/models/task.py for SQLAlchemy model
   - For Node.js: Check src/models/user.model.js for Mongoose schema

3. Check database configuration:
   - For Flask: app/extensions.py and app/__init__.py
   - For Node.js: src/config/db.js and src/index.js

4. Verify service layer implementation:
   - For Flask: app/services/task_service.py
   - For Node.js: src/services/user.service.js

5. Check for environment variables:
   - For Flask: .env.example for DATABASE_URI
   - For Node.js: .env.example for MONGODB_URI

## Iterating on Prompts

If the generated code doesn't meet expectations, modify the prompts in:
- `devspark/core/llm_interface.py` in the `get_ai_customized_template` function

Potential improvements to consider:
- Adding more specific examples in the prompt
- Providing clearer instructions for structuring database code
- Reinforcing naming conventions and best practices
