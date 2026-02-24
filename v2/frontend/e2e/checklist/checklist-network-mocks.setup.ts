import { test } from '@playwright/test';
import { mockChecklistAuthBootstrap } from './checklist-network-mocks';

// Register deterministic auth/bootstrap mocks for checklist tests that use pages.
test.beforeEach(async ({ page }) => {
  await mockChecklistAuthBootstrap(page);
});
