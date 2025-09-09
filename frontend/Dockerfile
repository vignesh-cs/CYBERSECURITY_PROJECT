FROM nginx:alpine

# Create a simple HTML file directly in the container
RUN echo "<html><body><h1>Compliance System</h1><p>Frontend is running!</p></body></html>" > /usr/share/nginx/html/index.html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]