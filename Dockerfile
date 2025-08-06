# Use a specific, stable version of Python 3.11 slim
FROM python:3.11.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the small, CPU-only version of torch FIRST
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Now, install the rest of the packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code
COPY . .

# Expose a default port (good practice, though Railway will override)
EXPOSE 8000

# --- FINAL CRITICAL FIX: The command to run your application ---
# This version explicitly uses a shell (`sh -c`) to ensure the `$PORT`
# environment variable provided by Railway is correctly interpreted.
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
