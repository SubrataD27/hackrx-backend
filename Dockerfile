# Use a specific, stable version of Python 3.11 slim
FROM python:3.11.8-slim

# Set environment variables to prevent Python from writing .pyc files
# and to ensure output is sent straight to the terminal without buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the file that lists the required Python packages
COPY requirements.txt .

# Install the Python packages
# This command is optimized to be faster and use less space.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code into the container
COPY . .

# Expose the port that your application will run on
EXPOSE 8000

# The command to run your application when the container starts.
# This uses the non-reloading, production-ready command.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
