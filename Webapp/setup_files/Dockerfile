FROM php:8.2-apache

# Habilitar módulos
RUN a2enmod rewrite

# Instalar dependências para o driver Cassandra
RUN apt-get update && \
    apt-get install -y \
    libuv1-dev \
    libssl-dev \
    libgmp-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar extensão Cassandra
RUN pecl install cassandra && \
    docker-php-ext-enable cassandra

# Copiar configuração do Apache
COPY setup_files/apache-config.conf /etc/apache2/sites-available/000-default.conf

# Copiar conteúdo da aplicação
COPY Web/ /var/www/html/