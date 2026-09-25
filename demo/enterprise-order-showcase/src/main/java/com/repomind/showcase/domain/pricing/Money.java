package com.repomind.showcase.domain.pricing;
import java.math.BigDecimal;
import java.math.RoundingMode;
public final class Money {
    private final BigDecimal amount;
    public Money(BigDecimal amount) { this.amount = amount.setScale(2, RoundingMode.HALF_UP); }
    public static Money of(String amount) { return new Money(new BigDecimal(amount)); }
    public BigDecimal amount() { return amount; }
    public Money add(Money other) { return new Money(amount.add(other.amount)); }
    public Money multiply(BigDecimal factor) { return new Money(amount.multiply(factor)); }
    @Override public String toString() { return amount.toPlainString(); }
}
