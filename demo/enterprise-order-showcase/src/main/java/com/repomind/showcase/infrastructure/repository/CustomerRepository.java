package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.customer.Customer;
public interface CustomerRepository { Customer findById(String id); }
