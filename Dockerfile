FROM python:latest

# Add app files to container
ADD admin.html main.py overlay.html .
ADD static ./static

# Install deps
RUN pip install requests auraxium uvicorn python-socketio

# Expose port 8080 over TCP
EXPOSE 8080/tcp

CMD [ "python", "./main.py" ]
