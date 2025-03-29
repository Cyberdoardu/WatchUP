FROM php:7.1-apache

# 1. Instalar dependências ESSENCIAIS
RUN apt-get update && \
    apt-get install -y \
    git \
    cmake \
    libuv1-dev \
    libssl-dev \
    libgmp-dev \
    wget \
    unzip \
    zlib1g-dev \
    libsasl2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 2. Instalar DataStax C++ Driver (versão COMPATÍVEL)
WORKDIR /tmp
RUN wget https://github.com/datastax/cpp-driver/archive/refs/tags/2.9.0.zip -O cpp-driver.zip && \
    unzip cpp-driver.zip && \
    mkdir cpp-driver-2.9.0/build && \
    cd cpp-driver-2.9.0/build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DCASS_BUILD_STATIC=ON && \
    make && \
    make install && \
    ldconfig && \
    rm -rf /tmp/cpp-driver-2.9.0

# 3. Instalar extensão Cassandra CORRETAMENTE
RUN pecl download cassandra-1.3.2 && \
    tar zxvf cassandra-1.3.2.tgz && \
    cd cassandra-1.3.2 && \
    phpize && \
    ./configure --with-cassandra=/usr && \
    make && \
    make install && \
    echo "extension=cassandra.so" > /usr/local/etc/php/conf.d/cassandra.ini && \
    rm -rf /tmp/cassandra-1.3.2*

# 4. Configurar Apache SIMPLIFICADO
RUN a2enmod rewrite
COPY setup_files/apache-config.conf /etc/apache2/sites-available/000-default.conf

# 5. Copiar aplicação
COPY Web/ /var/www/html/

# 6. Ajustar permissões
RUN chown -R www-data:www-data /var/www/html && \
    chmod -R 755 /var/www/html