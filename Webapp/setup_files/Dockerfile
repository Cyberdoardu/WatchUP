FROM php:8.2-apache

# 1. Instalar dependências
RUN apt-get update && \
    apt-get install -y \
    libpng-dev \
    libonig-dev \
    libxml2-dev \
    zip \
    unzip \
    && docker-php-ext-install mysqli pdo_mysql \
    && docker-php-ext-enable mysqli

# 2. Configurar Apache
RUN a2enmod rewrite
COPY setup_files/apache-config.conf /etc/apache2/sites-available/000-default.conf

# 3. Copiar aplicação
COPY Web/ /var/www/html/

# 4. Ajustar permissões
RUN chown -R www-data:www-data /var/www/html && \
    chmod -R 755 /var/www/html