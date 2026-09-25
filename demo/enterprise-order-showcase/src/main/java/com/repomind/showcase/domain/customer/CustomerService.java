package com.repomind.showcase.domain.customer;
import com.repomind.showcase.common.exception.CustomerException;
import com.repomind.showcase.infrastructure.repository.CustomerRepository;
public final class CustomerService {
    private final CustomerRepository repository;
    public CustomerService(CustomerRepository repository) { this.repository = repository; }
    public Customer validateCustomer(String id) {
        Customer customer = repository.findById(id);
        if (customer == null) throw new CustomerException("customer not found: " + id);
        if (customer.getAddress() == null) throw new CustomerException("shipping address missing: " + id);
        return customer;
    }
}
