SELECT order_id, cost_per_sack, total_cost, amount_paid, amount_change
FROM webapp_customerorder
WHERE
    TRIM(cost_per_sack) = '' OR
    TRIM(total_cost) = '' OR
    TRIM(amount_paid) = '' OR
    TRIM(amount_change) = '' OR
    cost_per_sack IS NULL OR
    total_cost IS NULL OR
    amount_paid IS NULL OR
    amount_change IS NULL
    OR
    -- Try to find non-numeric values (SQLite stores decimals as text sometimes)
    cost_per_sack GLOB '*[^0-9.]*'
    OR total_cost GLOB '*[^0-9.]*'
    OR amount_paid GLOB '*[^0-9.]*'
    OR amount_change GLOB '*[^0-9.]*'
;

DELETE FROM webapp_customerorder WHERE order_id = 72;