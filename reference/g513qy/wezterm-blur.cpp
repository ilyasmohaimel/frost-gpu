// SPDX-License-Identifier: GPL-2.0-only
// WezTerm's Wayland blur option cannot announce blur for an XWayland window.
// Bridge that request using KWin's X11 property, without changing opacity.
#include <xcb/xcb.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

class BlurBridge {
    xcb_connection_t *connection;
    xcb_window_t root;
    xcb_atom_t clients, blur, windowClass;

    xcb_atom_t atom(const char *name) {
        auto *reply = xcb_intern_atom_reply(connection,
            xcb_intern_atom(connection, 0, std::strlen(name), name), nullptr);
        if (!reply) std::exit(1);
        const auto result = reply->atom;
        std::free(reply);
        return result;
    }

    void update(xcb_window_t window) {
        // WM_CLASS can appear after MapNotify, so watch properties too.
        const uint32_t mask = XCB_EVENT_MASK_PROPERTY_CHANGE;
        xcb_change_window_attributes(connection, window, XCB_CW_EVENT_MASK, &mask);
        auto *klass = xcb_get_property_reply(connection,
            xcb_get_property(connection, 0, window, windowClass, XCB_ATOM_STRING, 0, 128), nullptr);
        if (!klass) return;
        const auto *data = static_cast<const char *>(xcb_get_property_value(klass));
        const auto size = xcb_get_property_value_length(klass);
        bool wezterm = false;
        for (int offset = 0; offset < size;) {
            const auto length = strnlen(data + offset, size - offset);
            if (std::string(data + offset, length) == "org.wezfurlong.wezterm") wezterm = true;
            offset += length + 1;
        }
        std::free(klass);
        if (!wezterm) return;
        auto *existing = xcb_get_property_reply(connection,
            xcb_get_property(connection, 0, window, blur, XCB_GET_PROPERTY_TYPE_ANY, 0, 1), nullptr);
        if (!existing) return;
        const bool missing = existing->type == XCB_ATOM_NONE;
        std::free(existing);
        if (missing) {
            const uint32_t wholeWindow = 0;
            xcb_change_property(connection, XCB_PROP_MODE_REPLACE, window, blur,
                                XCB_ATOM_CARDINAL, 32, 1, &wholeWindow);
            std::cout << "Blur request added to a WezTerm X11 window" << std::endl;
        }
    }

    void scan() {
        auto *reply = xcb_get_property_reply(connection,
            xcb_get_property(connection, 0, root, clients, XCB_ATOM_WINDOW, 0, 16384), nullptr);
        if (reply && reply->format == 32) {
            const auto *windows = static_cast<const xcb_window_t *>(xcb_get_property_value(reply));
            for (int i = 0; i < xcb_get_property_value_length(reply) / 4; ++i) update(windows[i]);
        }
        std::free(reply);
        xcb_flush(connection);
    }

public:
    BlurBridge() {
        int screenNumber = 0;
        connection = xcb_connect(nullptr, &screenNumber);
        if (xcb_connection_has_error(connection)) {
            std::cerr << "Cannot connect to the session X server" << std::endl;
            std::exit(1);
        }
        auto screens = xcb_setup_roots_iterator(xcb_get_setup(connection));
        while (screenNumber-- > 0) xcb_screen_next(&screens);
        root = screens.data->root;
        clients = atom("_NET_CLIENT_LIST");
        blur = atom("_KDE_NET_WM_BLUR_BEHIND_REGION");
        windowClass = atom("WM_CLASS");
        const uint32_t mask = XCB_EVENT_MASK_PROPERTY_CHANGE | XCB_EVENT_MASK_SUBSTRUCTURE_NOTIFY;
        xcb_change_window_attributes(connection, root, XCB_CW_EVENT_MASK, &mask);
    }

    ~BlurBridge() { xcb_disconnect(connection); }

    int run(bool once) {
        scan();
        if (once) return 0;
        while (auto *event = xcb_wait_for_event(connection)) {
            const auto type = event->response_type & ~0x80;
            if (type == XCB_PROPERTY_NOTIFY) {
                const auto *property = reinterpret_cast<xcb_property_notify_event_t *>(event);
                if (property->window == root && property->atom == clients) scan();
                else if (property->window != root && (property->atom == windowClass || property->atom == blur)) update(property->window);
            } else if (type == XCB_MAP_NOTIFY) {
                update(reinterpret_cast<xcb_map_notify_event_t *>(event)->window);
            }
            std::free(event);
            xcb_flush(connection);
        }
        return 1;
    }
};

int main(int argc, char **argv) {
    if (argc > 2 || (argc == 2 && std::strcmp(argv[1], "--once") != 0)) return 2;
    BlurBridge bridge;
    return bridge.run(argc == 2);
}
