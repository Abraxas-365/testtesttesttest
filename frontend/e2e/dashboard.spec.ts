import { test, expect, type Page } from "@playwright/test";

const PROOF_DIR = "/workspace/proof";

// Delete every existing expense via the API so the test starts from a known
// empty state. The Vite dev server proxies /api to the Go backend.
async function clearAllExpenses(page: Page) {
  const res = await page.request.get("/api/expenses");
  const expenses: Array<{ id: number }> = await res.json();
  for (const e of expenses) {
    await page.request.delete(`/api/expenses/${e.id}`);
  }
}

test.describe("Expense Dashboard", () => {
  test("empty state, add expenses, pie chart, and delete", async ({ page }) => {
    await clearAllExpenses(page);

    // 1. Empty state ---------------------------------------------------------
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Expense Dashboard" })).toBeVisible();
    await expect(page.getByTestId("empty-state")).toBeVisible();
    await expect(page.getByTestId("total")).toHaveText("Total: $0.00");

    await page.screenshot({
      path: `${PROOF_DIR}/screenshot-1-empty-state.png`,
      fullPage: true,
    });

    // 2. Add several expenses across categories ------------------------------
    const items = [
      { amount: "25.50", category: "food", description: "Groceries", date: "2024-01-10" },
      { amount: "60.00", category: "transport", description: "Gas", date: "2024-01-11" },
      { amount: "120.00", category: "housing", description: "Internet bill", date: "2024-01-12" },
      { amount: "15.00", category: "food", description: "Lunch", date: "2024-01-13" },
    ];

    for (const item of items) {
      await page.getByLabel("Amount").fill(item.amount);
      await page.getByLabel("Category").selectOption(item.category);
      await page.getByLabel("Description").fill(item.description);
      await page.getByLabel("Date").fill(item.date);
      await page.getByRole("button", { name: "Add Expense" }).click();
      // Wait until the new row appears before adding the next one.
      await expect(
        page.getByTestId("expense-row").filter({ hasText: item.description })
      ).toBeVisible();
    }

    // Table should show all four rows.
    await expect(page.getByTestId("expense-row")).toHaveCount(4);
    // Total = 25.50 + 60 + 120 + 15 = 220.50
    await expect(page.getByTestId("total")).toHaveText("Total: $220.50");

    // Pie chart should be rendered with category slices.
    const chart = page.getByTestId("category-pie-chart");
    await expect(chart).toBeVisible();
    await expect(chart.locator("svg .recharts-pie-sector").first()).toBeVisible();

    await page.screenshot({
      path: `${PROOF_DIR}/screenshot-2-with-expenses.png`,
      fullPage: true,
    });

    // 3. Delete an expense and confirm the view refreshes --------------------
    const housingRow = page
      .getByTestId("expense-row")
      .filter({ hasText: "Internet bill" });
    await housingRow.getByRole("button", { name: /Delete expense/ }).click();

    await expect(page.getByTestId("expense-row")).toHaveCount(3);
    await expect(
      page.getByTestId("expense-row").filter({ hasText: "Internet bill" })
    ).toHaveCount(0);
    // Total after removing 120.00 = 100.50
    await expect(page.getByTestId("total")).toHaveText("Total: $100.50");

    await page.screenshot({
      path: `${PROOF_DIR}/screenshot-3-after-delete.png`,
      fullPage: true,
    });
  });
});
