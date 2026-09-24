# RepoMind Order Demo

This small Java repository contains the Phase 1 call chain and a deliberately simple NullPointerException for RepoMind fault-localization validation.

Expected call chain:

```text
OrderController.createOrder
  -> OrderService.createOrder
    -> InventoryService.checkStock
      -> InventoryRepository.findStock
```

`InventoryRepository.findStock()` returns `null`; `InventoryService.checkStock()` then reads `stock.available` without a null check.
