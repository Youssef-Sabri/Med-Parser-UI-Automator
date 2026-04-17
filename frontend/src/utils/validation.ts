// Clinical field validation utilities

import { DEA_REGEX, DATE_REGEX } from '../services/config';

/**
 * Validate DEA number format and checksum.
 * DEA format: 2 letters + 7 digits
 * Checksum: (1st + 3rd + 5th digit) + 2 * (2nd + 4th + 6th digit) mod 10 = 7th digit
 */
export function validateDEA(dea: string): { valid: boolean; error?: string } {
  if (!dea) return { valid: true }; // Optional field
  
  const trimmed = dea.trim().toUpperCase();
  
  if (!DEA_REGEX.test(trimmed)) {
    return { valid: false, error: 'DEA must be 2 letters followed by 7 digits (e.g., AB1234567)' };
  }
  
  // Checksum validation
  const digits = trimmed.slice(2);
  const sum =
    parseInt(digits[0], 10) +
    parseInt(digits[2], 10) +
    parseInt(digits[4], 10) +
    2 * (parseInt(digits[1], 10) + parseInt(digits[3], 10) + parseInt(digits[5], 10));
  
  const checkDigit = sum % 10;
  const expectedCheckDigit = parseInt(digits[6], 10);
  
  if (checkDigit !== expectedCheckDigit) {
    return { valid: false, error: 'Invalid DEA checksum' };
  }
  
  return { valid: true };
}

/**
 * Validate date format (YYYY-MM-DD or MM/DD/YYYY)
 */
export function validateDate(date: string): { valid: boolean; error?: string } {
  if (!date) return { valid: true }; // Optional field
  
  if (!DATE_REGEX.test(date.trim())) {
    return { valid: false, error: 'Date must be YYYY-MM-DD or MM/DD/YYYY' };
  }
  
  const parsed = new Date(date);
  if (isNaN(parsed.getTime())) {
    return { valid: false, error: 'Invalid date' };
  }
  
  return { valid: true };
}

/**
 * Validate dosage field (should contain a number)
 */
export function validateDosage(dosage: string): { valid: boolean; error?: string } {
  if (!dosage) return { valid: true }; // Optional field
  
  const hasNumber = /\d+/.test(dosage);
  if (!hasNumber) {
    return { valid: false, error: 'Dosage should contain a numeric value' };
  }
  
  return { valid: true };
}

/**
 * Validate quantity (must be positive number)
 */
export function validateQuantity(quantity: string): { valid: boolean; error?: string } {
  if (!quantity) return { valid: true }; // Optional field
  
  const num = parseFloat(quantity);
  if (isNaN(num) || num <= 0) {
    return { valid: false, error: 'Quantity must be a positive number' };
  }
  
  if (num > 9999) {
    return { valid: false, error: 'Quantity seems unusually high' };
  }
  
  return { valid: true };
}

/**
 * Validate refills (must be non-negative integer or "PRN")
 */
export function validateRefills(refills: string): { valid: boolean; error?: string } {
  if (!refills) return { valid: true }; // Optional field
  
  const trimmed = refills.trim().toUpperCase();
  if (trimmed === 'PRN') return { valid: true };
  
  const num = parseInt(trimmed, 10);
  if (isNaN(num) || num < 0) {
    return { valid: false, error: 'Refills must be a non-negative number or PRN' };
  }
  
  if (num > 99) {
    return { valid: false, error: 'Refills seems unusually high' };
  }
  
  return { valid: true };
}
