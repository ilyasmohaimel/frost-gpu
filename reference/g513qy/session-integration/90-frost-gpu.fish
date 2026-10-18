status is-interactive; or return
if test "$FROST_GPU_LIVE_SESSION" = 1
    if test "$FROST_GPU_WRAPPED" = 1; or test "$VK_DRIVER_FILES" = /opt/frost-gpu/share/zss_icd.json
        if test "$FROST_GPU_FIXED_IGPU" = 1
            set --export --global MESA_VK_DEVICE_SELECT 1002:1638
            set --export --global MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE 0
            set --erase --global FROST_GPU_FIXED_IGPU
        end
        for name in VK_DRIVER_FILES VK_ICD_FILENAMES ZSS_START_ON ZSS_RETAIN ZSS_REAL_DRIVER_FILES ZSS_MANIFEST MESA_LOADER_DRIVER_OVERRIDE GALLIUM_DRIVER __GLX_VENDOR_LIBRARY_NAME __EGL_VENDOR_LIBRARY_FILENAMES LIBGL_KOPPER_DRI2 QSG_RHI_BACKEND GDK_BACKEND QT_QPA_PLATFORM QT_XCB_GL_INTEGRATION
            set --erase --global $name
        end
        if set --query FROST_GPU_WAYLAND_DISPLAY
            set --export --global WAYLAND_DISPLAY $FROST_GPU_WAYLAND_DISPLAY
        end
        set --erase --global FROST_GPU_WAYLAND_DISPLAY
        set --erase --global FROST_GPU_WRAPPED
    end
end
