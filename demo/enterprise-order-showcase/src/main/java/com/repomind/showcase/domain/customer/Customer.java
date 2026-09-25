package com.repomind.showcase.domain.customer;
public final class Customer {
    private final String id;
    private final String email;
    private final boolean member;
    private final boolean smsPreferred;
    private final Address address;
    public Customer(String id, String email, boolean member, boolean smsPreferred, Address address) {
        this.id = id; this.email = email; this.member = member; this.smsPreferred = smsPreferred; this.address = address;
    }
    public String getId() { return id; }
    public String getEmail() { return email; }
    public boolean isMember() { return member; }
    public boolean isSmsPreferred() { return smsPreferred; }
    public Address getAddress() { return address; }
}
