# Use a specific, stable version of Python 3.11 slim
FROM python:3.11.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# --- CRITICAL FIX: Install the small, CPU-only version of torch FIRST ---
# This prevents the massive GPU version from being installed later.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# --- Now, install the rest of the packages ---
# This command is optimized for speed and size.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code
COPY . .

# Expose the port your application runs on
EXPOSE 8000

# The command to run your application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
