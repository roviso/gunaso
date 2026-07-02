import { defineStore } from 'pinia'
import { ref } from 'vue'
import { organizationsAPI } from '@/api/organizations'

const MOCK_ORGS = [
  {
    id: 1, slug: 'nepal-telecom', name: 'Nepal Telecom', category: 'Telecom',
    description: 'State-owned telecommunications company of Nepal providing internet, mobile, and landline services across the country.',
    verified: true, logo: null, submission_count: 1247, avg_resolution_days: 8,
    website: 'https://www.ntc.net.np', resolved_percent: 76
  },
  {
    id: 2, slug: 'ncell', name: 'Ncell', category: 'Telecom',
    description: 'Private telecommunications company providing mobile and data services across Nepal with nationwide coverage.',
    verified: true, logo: null, submission_count: 934, avg_resolution_days: 5,
    website: 'https://www.ncell.axiata.com', resolved_percent: 82
  },
  {
    id: 3, slug: 'nea', name: 'Nepal Electricity Authority', category: 'Government',
    description: 'Government-owned corporation responsible for generation, transmission, and distribution of electricity in Nepal.',
    verified: true, logo: null, submission_count: 2103, avg_resolution_days: 14,
    website: 'https://www.nea.org.np', resolved_percent: 68
  },
  {
    id: 4, slug: 'nrb', name: 'Nepal Rastra Bank', category: 'Bank',
    description: 'Central bank of Nepal responsible for monetary policy, banking supervision, and financial sector regulation.',
    verified: true, logo: null, submission_count: 412, avg_resolution_days: 10,
    website: 'https://www.nrb.org.np', resolved_percent: 89
  },
  {
    id: 5, slug: 'bir-hospital', name: 'Bir Hospital', category: 'Hospital',
    description: 'The oldest and largest public hospital in Nepal providing comprehensive healthcare services to citizens.',
    verified: true, logo: null, submission_count: 756, avg_resolution_days: 7,
    website: 'https://www.birhospital.gov.np', resolved_percent: 71
  },
  {
    id: 6, slug: 'ktm-metro', name: 'Kathmandu Metropolitan City', category: 'Government',
    description: 'Local government body responsible for urban planning, infrastructure, and civic services in the Kathmandu metro area.',
    verified: false, logo: null, submission_count: 589, avg_resolution_days: 18,
    website: 'https://kathmandumetro.gov.np', resolved_percent: 55
  },
  {
    id: 7, slug: 'nabil-bank', name: 'Nabil Bank', category: 'Bank',
    description: 'One of Nepal\'s leading private commercial banks offering retail, corporate, and digital banking services.',
    verified: true, logo: null, submission_count: 328, avg_resolution_days: 4,
    website: 'https://www.nabilbank.com', resolved_percent: 91
  },
  {
    id: 8, slug: 'patan-hospital', name: 'Patan Hospital', category: 'Hospital',
    description: 'A leading teaching hospital in Nepal known for quality healthcare and medical education.',
    verified: true, logo: null, submission_count: 445, avg_resolution_days: 6,
    website: 'https://www.patanhospital.org.np', resolved_percent: 78
  }
]

export const useOrganizationStore = defineStore('organization', () => {
  const organizations = ref([])
  const currentOrg = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const totalCount = ref(0)

  async function fetchOrganizations(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await organizationsAPI.list(params)
      organizations.value = data.results || data
      totalCount.value = data.count || organizations.value.length
    } catch {
      organizations.value = MOCK_ORGS
      totalCount.value = MOCK_ORGS.length
    } finally {
      loading.value = false
    }
  }

  async function fetchOrgBySlug(slug) {
    loading.value = true
    error.value = null
    currentOrg.value = null
    try {
      const { data } = await organizationsAPI.getBySlug(slug)
      currentOrg.value = data
    } catch {
      currentOrg.value = MOCK_ORGS.find((o) => o.slug === slug) || null
      if (!currentOrg.value) error.value = 'Organization not found.'
    } finally {
      loading.value = false
    }
  }

  function getMockOrgs() { return MOCK_ORGS }

  return {
    organizations, currentOrg, loading, error, totalCount,
    fetchOrganizations, fetchOrgBySlug, getMockOrgs
  }
})
