package com.repomind.showcase.api.request;
public final class PaymentRequest {
    private final String method;
    public PaymentRequest(String method) { this.method = method; }
    public String getMethod() { return method; }
}
