package com.repomind.showcase.domain.pricing;
import java.math.BigDecimal;
public final class Promotion {
    private final String code;
    private final BigDecimal multiplier;
    public Promotion(String code, BigDecimal multiplier) { this.code = code; this.multiplier = multiplier; }
    public String getCode() { return code; }
    public BigDecimal getMultiplier() { return multiplier; }
}
