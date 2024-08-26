-- postgreSQL query

WITH RecentOrderItems AS (
    SELECT
        o.customer_id,
        oi.product_id,
        oi.quantity * oi.price_per_unit AS spent
    FROM
        Orders o
    JOIN
        Order_Items oi ON o.order_id = oi.order_id
    WHERE
        o.order_date >= CURRENT_DATE - INTERVAL '1 year'
),
CustomerTotalSpent AS (
    SELECT
        customer_id,
        SUM(spent) AS total_spent
    FROM
        RecentOrderItems
    GROUP BY
        customer_id
),
CategorySpending AS (
    SELECT
        r.customer_id,
        p.category,
        SUM(r.spent) AS category_spent
    FROM
        RecentOrderItems r
    JOIN
        Products p ON r.product_id = p.product_id
    GROUP BY
        r.customer_id, p.category
),
RankedCategories AS (
    SELECT
        customer_id,
        category,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY category_spent DESC) AS rank
    FROM
        CategorySpending cs
)
SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    cs.total_spent,
    rc.category AS most_purchased_category
FROM
    CustomerTotalSpent cs
JOIN
    Customers c ON cs.customer_id = c.customer_id
JOIN
    RankedCategories rc ON cs.customer_id = rc.customer_id AND rc.rank = 1
ORDER BY
    cs.total_spent DESC
LIMIT 5;
