// SPDX-License-Identifier: GPL-2.0-only
#include <wayland-client.h>
#include "dmabuf-client.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysmacros.h>
#include <unistd.h>

static struct zwp_linux_dmabuf_v1 *dmabuf;
static struct wl_compositor *compositor;
static dev_t main_device;
static unsigned requested_version = 4;

static void feedback_done(void *data, struct zwp_linux_dmabuf_feedback_v1 *feedback)
{
    printf("device %u:%u\n", major(main_device), minor(main_device));
    fflush(stdout);
}

static void format_table(void *data, struct zwp_linux_dmabuf_feedback_v1 *feedback,
                         int32_t fd, uint32_t size)
{
    close(fd);
}

static void main_device_changed(void *data, struct zwp_linux_dmabuf_feedback_v1 *feedback,
                                struct wl_array *device)
{
    if (device->size != sizeof(main_device)) {
        fprintf(stderr, "Invalid main_device size\n");
        exit(3);
    }
    memcpy(&main_device, device->data, sizeof(main_device));
}

static void tranche_done(void *data, struct zwp_linux_dmabuf_feedback_v1 *feedback) {}
static void tranche_target(void *data, struct zwp_linux_dmabuf_feedback_v1 *feedback,
                           struct wl_array *device) {}
static void tranche_formats(void *data, struct zwp_linux_dmabuf_feedback_v1 *feedback,
                            struct wl_array *formats) {}
static void tranche_flags(void *data, struct zwp_linux_dmabuf_feedback_v1 *feedback,
                          uint32_t flags) {}

static const struct zwp_linux_dmabuf_feedback_v1_listener feedback_listener = {
    .done = feedback_done,
    .format_table = format_table,
    .main_device = main_device_changed,
    .tranche_done = tranche_done,
    .tranche_target_device = tranche_target,
    .tranche_formats = tranche_formats,
    .tranche_flags = tranche_flags,
};

static void global_added(void *data, struct wl_registry *registry, uint32_t id,
                         const char *name, uint32_t version)
{
    if (strcmp(name, "wl_compositor") == 0) {
        compositor = wl_registry_bind(registry, id, &wl_compositor_interface,
                                      version < 4 ? version : 4);
    }
    if (strcmp(name, "zwp_linux_dmabuf_v1") == 0) {
        if (version < requested_version) {
            fprintf(stderr, "DMA-BUF version %u is unavailable\n", requested_version);
            exit(3);
        }
        dmabuf = wl_registry_bind(registry, id, &zwp_linux_dmabuf_v1_interface,
                                  requested_version);
    }
}

static void global_removed(void *data, struct wl_registry *registry, uint32_t id) {}
static const struct wl_registry_listener registry_listener = {
    .global = global_added,
    .global_remove = global_removed,
};

int main(int argc, char **argv)
{
    if (argc != 3 || (atoi(argv[1]) != 4 && atoi(argv[1]) != 5)) {
        fprintf(stderr, "usage: client VERSION(4|5) PER_SURFACE(0|1)\n");
        return 2;
    }
    requested_version = (unsigned)atoi(argv[1]);
    struct wl_display *display = wl_display_connect(NULL);
    if (!display) {
        return 1;
    }
    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    if (wl_display_roundtrip(display) < 0 || !dmabuf || !compositor) {
        return 2;
    }
    struct zwp_linux_dmabuf_feedback_v1 *feedback;
    if (atoi(argv[2])) {
        struct wl_surface *surface = wl_compositor_create_surface(compositor);
        feedback = zwp_linux_dmabuf_v1_get_surface_feedback(dmabuf, surface);
    } else {
        feedback = zwp_linux_dmabuf_v1_get_default_feedback(dmabuf);
    }
    zwp_linux_dmabuf_feedback_v1_add_listener(feedback, &feedback_listener, NULL);
    while (wl_display_dispatch(display) >= 0) {}
    return 0;
}
