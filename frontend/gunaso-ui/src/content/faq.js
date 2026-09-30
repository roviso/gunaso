// FAQ copy shared by the landing page (first few) and /how-it-works (all).
// Every answer must describe how the platform actually behaves today — see
// CLAUDE.md; don't promise roadmap features here.
export const citizenFaq = [
  {
    q: 'Do I need an account to file a gunaso?',
    a: 'No. Anyone can file a complaint, feedback or suggestion without signing up. A free account simply keeps all your cases in one dashboard.',
  },
  {
    q: 'Can the organization see who I am if I file anonymously?',
    a: 'No. When you choose "Submit anonymously", your name, email and phone are never shown to the organization — not in their dashboard, not in exports, not in notifications. Only Gunaso platform staff can see identity, for abuse handling.',
  },
  {
    q: 'How do I follow up on my gunaso?',
    a: 'Right after submitting you get a reference number (like GUN-2026-12345) and a private follow-up link. Anyone can check the status with the reference number; only the private link lets you reply to the organization and rate the outcome. If you gave an email, we send you the link and notify you whenever something changes.',
  },
  {
    q: 'What if the organization ignores my gunaso?',
    a: 'Every case is on a public, time-stamped timeline that organizations cannot edit or delete. Cases left unanswered past the response target are flagged as overdue to the organization, and each organization\'s resolution rate and citizen rating are public.',
  },
  {
    q: 'Can I attach photos or documents?',
    a: 'Yes — images (JPG, PNG, GIF, WebP), PDF and Word documents are accepted. Every file is checked for size, type and actual content before it is stored.',
  },
  {
    q: 'What does it cost?',
    a: 'Nothing, for citizens. Filing and tracking a gunaso is free and always will be.',
  },
]

export const organizationFaq = [
  {
    q: 'How does my organization join Gunaso?',
    a: 'Create an account, register your organization, and our team verifies it. Once verified, you appear in the public directory and on the map, and citizens can start reaching you.',
  },
  {
    q: 'Can we track complaints per branch or office?',
    a: 'Yes. Add each branch with its location and print its QR code. A gunaso filed by scanning a branch\'s code is tagged to that branch, so your dashboard and hotspot map show exactly where issues come from.',
  },
  {
    q: 'Can our team work on cases together?',
    a: 'Yes. Invite staff by email, create roles with exactly the permissions they need (view, manage, assign, reports…), assign cases, and keep internal notes that citizens never see.',
  },
  {
    q: 'Can we export our data?',
    a: 'Yes. Download any filtered view of your submissions as a spreadsheet-ready CSV. Anonymous submitters stay anonymous in exports too.',
  },
]
