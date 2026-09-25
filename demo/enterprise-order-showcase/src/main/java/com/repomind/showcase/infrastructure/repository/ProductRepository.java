package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.product.Product;
public interface ProductRepository { Product findBySku(String sku); }
