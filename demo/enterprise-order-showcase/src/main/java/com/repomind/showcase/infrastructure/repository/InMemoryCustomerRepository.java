package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.customer.Customer;
import java.util.HashMap;
import java.util.Map;
public final class InMemoryCustomerRepository implements CustomerRepository {
    private final Map<String, Customer> customers = new HashMap<>();
    public void add(Customer customer) { customers.put(customer.getId(), customer); }
    @Override public Customer findById(String id) { return customers.get(id); }
}
