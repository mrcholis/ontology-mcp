FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements311.txt .
RUN pip install --no-cache-dir -r requirements311.txt

# Copy source code
COPY src/ src/
COPY mcp_server.py .
COPY xml_files/ xml_files/
# output/ directory not present in repo; generated at runtime if needed
COPY demo.py .

# Default: run the MCP server (stdio mode)
# Override CMD to run the demo instead: docker run ... python demo.py
CMD ["python", "mcp_server.py"]
