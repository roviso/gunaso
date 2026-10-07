import { Capacitor, SystemBars, SystemBarsStyle } from '@capacitor/core'
import { App } from '@capacitor/app'
import { SplashScreen } from '@capacitor/splash-screen'

// True inside the Android/iOS app shell, false on the web build.
export const isNative = Capacitor.isNativePlatform()

/** Wire native-only behaviour (hardware back button, system bars, splash). No-op on web. */
export function setupNative(router) {
  if (!isNative) return
  document.documentElement.classList.add('native')

  // Android back button: go back in-app, exit only from the root screen.
  App.addListener('backButton', ({ canGoBack }) => {
    if (canGoBack && router.currentRoute.value.path !== '/') router.back()
    else App.exitApp()
  })

  syncSystemBars()
  new MutationObserver(syncSystemBars).observe(document.documentElement, { attributeFilter: ['class'] })

  router.isReady().then(() => SplashScreen.hide())
}

// Status/navigation bar icons follow the app's own dark-mode class, not the OS theme.
function syncSystemBars() {
  const dark = document.documentElement.classList.contains('dark')
  SystemBars.setStyle({ style: dark ? SystemBarsStyle.Dark : SystemBarsStyle.Light })
}
