<script setup>
// /org/dashboard renders a different component per role, kept under one
// route name ('OrgDashboard') so existing redirects (ChangePasswordPage,
// AcceptInvitePage, router guards) don't need to know which one they're
// sending the user to.
import { useAuthStore } from '@/stores/auth'
import OrgDashboardPage from './OrgDashboardPage.vue'
import StaffDashboardPage from './StaffDashboardPage.vue'

const authStore = useAuthStore()
</script>

<template>
  <OrgDashboardPage v-if="authStore.isOrgAdmin" />
  <StaffDashboardPage v-else />
</template>
