# Source only. Clear the GUI parent's renderer settings for interactive shells.
case $- in
*i*)
    if [ "${FROST_GPU_LIVE_SESSION:-0}" = 1 ] && { [ "${FROST_GPU_WRAPPED:-0}" = 1 ] || [ "${VK_DRIVER_FILES:-}" = /opt/frost-gpu/share/zss_icd.json ]; }; then
        if [ "${FROST_GPU_FIXED_IGPU:-0}" = 1 ]; then
            export MESA_VK_DEVICE_SELECT=1002:1638 MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE=0
            unset FROST_GPU_FIXED_IGPU
        fi
        unset VK_DRIVER_FILES VK_ICD_FILENAMES ZSS_START_ON ZSS_RETAIN ZSS_REAL_DRIVER_FILES ZSS_MANIFEST
        unset MESA_LOADER_DRIVER_OVERRIDE GALLIUM_DRIVER __GLX_VENDOR_LIBRARY_NAME __EGL_VENDOR_LIBRARY_FILENAMES LIBGL_KOPPER_DRI2
        unset QSG_RHI_BACKEND GDK_BACKEND QT_QPA_PLATFORM QT_XCB_GL_INTEGRATION
        if [ "${FROST_GPU_WAYLAND_DISPLAY+x}" = x ]; then
            export WAYLAND_DISPLAY="$FROST_GPU_WAYLAND_DISPLAY"
        fi
        unset FROST_GPU_WAYLAND_DISPLAY FROST_GPU_WRAPPED
    fi
    ;;
esac
