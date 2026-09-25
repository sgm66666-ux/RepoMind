package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.inventory.Stock;
public interface InventoryRepository { Stock findAvailableStock(String sku); }
