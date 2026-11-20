FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Remove the default Nginx page
RUN rm -rf ./*

# Copy the website files
COPY index.html .
COPY main.js .
COPY style.css .

# Copy map components and supporting assets
COPY code/map/ ./code/map/

EXPOSE 80
