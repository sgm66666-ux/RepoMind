package com.repomind.showcase.domain.product;
import com.repomind.showcase.common.exception.BusinessException;
import com.repomind.showcase.infrastructure.repository.ProductRepository;
public final class ProductService {
    private final ProductRepository repository;
    public ProductService(ProductRepository repository) { this.repository = repository; }
    public Product loadProduct(String sku) {
        Product product = repository.findBySku(sku);
        if (product == null || !product.isActive()) throw new BusinessException("product unavailable: " + sku);
        return product;
    }
}
