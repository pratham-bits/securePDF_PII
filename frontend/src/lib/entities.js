const LABELS = {
  AADHAAR: 'Aadhaar number',
  AADHAAR_VID: 'Aadhaar virtual ID',
  PAN: 'PAN',
  PASSPORT_IN: 'Passport number',
  VOTER_ID: 'Voter ID',
  DRIVING_LICENCE: 'Driving licence',
  CREDIT_CARD: 'Card number',
  BANK_ACCOUNT: 'Bank account number',
  IFSC: 'IFSC code',
  GSTIN: 'GSTIN',
  UPI_ID: 'UPI ID',
  VEHICLE_REG: 'Vehicle number',
  DATE_OF_BIRTH: 'Date of birth',
  EMAIL: 'Email address',
  PHONE_IN: 'Phone number',
  MANUAL: 'Box added by you',
}

export function entityLabel(type) {
  if (LABELS[type]) return LABELS[type]
  const words = type.toLowerCase().replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export const TIER_ORDER = ['mandatory', 'recommended', 'optional', 'manual']

export const TIER_TITLES = {
  mandatory: 'Sensitive (redacted by default)',
  recommended: 'Personal details',
  optional: 'Other',
  manual: 'Your boxes',
}