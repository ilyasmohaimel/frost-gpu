#include <unistd.h>
#include <QApplication>
#include <QSystemTrayIcon>
#include <QMenu>
#include <QTimer>
#include <QPainter>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QDir>
#include <QDateTime>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QDBusVariant>
#include <QTextStream>

static QString textFile(const QString &path) {
    QFile file(path);
    return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()).trimmed() : QString();
}
struct PowerSource { QString label; bool useRx; };
static PowerSource readPowerSource() {
    const QDir supplies("/sys/class/power_supply");
    bool usb = false, barrel = false, external = false, pd = false;
    for (const QString &name : supplies.entryList(QDir::Dirs | QDir::NoDotAndDotDot)) {
        const QString base = supplies.filePath(name);
        const QString type = textFile(base + "/type");
        if (type == "Battery" || textFile(base + "/online").toInt() <= 0) continue;
        external = true;
        if (type.startsWith("USB") || name.startsWith("ucsi-source-psy-")) {
            usb = true;
            const QString protocol = textFile(base + "/usb_type");
            pd = pd || protocol.contains("[PD]") || protocol.contains("[PD_PPS]") || type.startsWith("USB_PD");
        }
        if (name == "ADP0" && type == "Mains") barrel = true;
    }
    if (usb) return {pd ? "USB-C PD" : "USB-C power", false};
    if (barrel) return {"Barrel charger", true};
    return {external ? "External power" : "Battery", false};
}
static QString gpuName(const QString &node) {
    if (node.isEmpty()) return "Unknown";
    for (const auto &pair : {qMakePair(QString("0000:07:00.0"), QString("iGPU")),
                            qMakePair(QString("0000:03:00.0"), QString("RX 6800M"))}) {
        const QString resolved = QFileInfo("/dev/dri/by-path/pci-" + pair.first + "-render").canonicalFilePath();
        if (!resolved.isEmpty() && (resolved == node || node == pair.first)) return pair.second;
    }
    return "Unknown";
}
static QIcon chipIcon(const QString &mode, bool warning) {
    QIcon icon;
    for (int size : {22, 32, 48, 64, 128}) {
        QPixmap pix(size, size); pix.fill(Qt::transparent);
        QPainter p(&pix); p.setRenderHint(QPainter::Antialiasing);
        p.scale(size / 64., size / 64.);
        const QColor color(warning ? "#F3C773" : mode == "iGPU" ? "#8DC9FF" : mode == "RX 6800M" ? "#FF9E99" : "#BBC2CC");
        p.setPen(QPen(color, 3.5, Qt::SolidLine, Qt::RoundCap));
        for (int n : {22, 32, 42}) {
            p.drawLine(QPointF(n, 4), QPointF(n, 10)); p.drawLine(QPointF(n, 54), QPointF(n, 60));
            p.drawLine(QPointF(4, n), QPointF(10, n)); p.drawLine(QPointF(54, n), QPointF(60, n));
        }
        p.setBrush(QColor("#20252C")); p.drawRoundedRect(QRectF(11, 11, 42, 42), 7, 7);
        QFont f = QApplication::font(); f.setBold(true); f.setPixelSize(mode == "RX 6800M" ? 22 : 34);
        p.setFont(f); p.setPen(color);
        p.drawText(QRectF(11, 9, 42, 44), Qt::AlignCenter, warning && mode == "Unknown" ? "!" : mode == "iGPU" ? "i" : mode == "RX 6800M" ? "RX" : "?");
        p.end(); icon.addPixmap(pix);
    }
    return icon;
}

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    app.setApplicationName("frost-gpu-indicator");
    app.setApplicationDisplayName("Frost GPU mode");
    app.setDesktopFileName("frost-gpu-indicator");
    app.setQuitOnLastWindowClosed(false);
    if (!QDBusConnection::sessionBus().registerService("io.frost.GpuIndicator")) return 0;
    const QString runtime = qEnvironmentVariable("XDG_RUNTIME_DIR", "/run/user/" + QString::number(getuid()));
    const QString statePath = runtime + "/frost-gpu-live/status.json";
    const QString config = qEnvironmentVariable("XDG_CONFIG_HOME", QDir::homePath() + "/.config");
    QSystemTrayIcon tray;
    QMenu menu;
    QAction *renderer = menu.addAction("Desktop renderer: checking…"); renderer->setEnabled(false);
    QAction *power = menu.addAction("Power: checking…"); power->setEnabled(false);
    QAction *automatic = menu.addAction("Automatic switching: checking…"); automatic->setEnabled(false);
    QAction *switching = menu.addAction("Switch status: checking…"); switching->setEnabled(false);
    QAction *rxPower = menu.addAction("RX power: checking…"); rxPower->setEnabled(false);
    menu.addSeparator();
    QAction *scope = menu.addAction("Shows desktop mode; some apps stay on iGPU."); scope->setEnabled(false);
    menu.addSeparator();
    QAction *refresh = menu.addAction("Refresh status");
    QAction *quit = menu.addAction("Quit indicator");
    QObject::connect(quit, &QAction::triggered, &app, &QApplication::quit);
    tray.setContextMenu(&menu);
    QString currentNode;
    QString dbusError;
    bool pending = false;
    bool queried = false;
    QByteArray lastDisplay;
    auto render = [&]() {
        QFile file(statePath);
        QJsonObject state;
        if (file.open(QIODevice::ReadOnly)) state = QJsonDocument::fromJson(file.readAll()).object();
        const auto input = readPowerSource();
        const bool ac = input.useRx;
        const QString source = input.label;
        const QString mode = queried && dbusError.isEmpty() ? gpuName(currentNode) : "Unknown";
        const bool disabled = QFileInfo::exists(config + "/frost-gpu-live/disabled");
        const bool fallback = QFileInfo::exists(runtime + "/frost-gpu-live/fallback");
        const double age = QDateTime::currentSecsSinceEpoch() - state.value("updatedAt").toDouble();
        const bool fresh = !state.isEmpty() && age >= -5 && age < 30;
        const bool frostSession = !textFile(runtime + "/frost-gpu-live/login-session").isEmpty()
            && textFile(runtime + "/frost-gpu-live/login-session") == qEnvironmentVariable("XDG_SESSION_ID");
        QString status = state.value("state").toString();
        QString detail;
        bool warning = disabled || fallback || !fresh || !frostSession || mode == "Unknown";
        if (disabled) detail = "Automatic switching disabled";
        else if (fallback) detail = "Stock renderer fallback";
        else if (!frostSession) detail = "Frost session inactive";
        else if (!fresh) detail = "Controller not responding";
        else if (!dbusError.isEmpty()) detail = "Renderer unavailable";
        else if (status == "steady" && state.value("ac").toBool() == ac && gpuName(state.value("target").toString()) == mode)
            detail = "Ready";
        else if (status == "steady" || status == "power-changed" || status == "retry")
            detail = "Switching to " + QString(ac ? "RX 6800M" : "iGPU") + "…";
        else { warning = true; detail = status == "blocked" ? "Switch blocked" : status == "halted" ? "Switch halted" : "Switch unavailable"; }
        const QString rxRuntime = textFile("/sys/bus/pci/devices/0000:03:00.0/power/runtime_status");
        const QString pci = textFile("/sys/bus/pci/devices/0000:03:00.0/power_state");
        const QString rx = rxRuntime == "suspended" && pci == "D3cold" ? "Off (D3cold)" :
                           rxRuntime == "suspended" ? "Suspended (" + pci + ")" :
                           rxRuntime == "active" ? "Powered on" : "Unknown";
        const QString title = mode + " · " + source;
        QStringList tooltip{title, detail, "RX power: " + rx};
        if (warning && !state.value("error").toString().isEmpty()) tooltip << state.value("error").toString().left(240);
        const QByteArray display = (tooltip.join('\n') + QString::number(warning)).toUtf8();
        if (display != lastDisplay) {
            tray.setIcon(chipIcon(mode, warning)); tray.setToolTip(tooltip.join('\n')); lastDisplay = display;
            renderer->setText("Desktop renderer: " + mode);
            power->setText("Power: " + source);
            automatic->setText("Automatic switching: " + QString(disabled || fallback || !fresh || !frostSession ? "Inactive" : "Enabled"));
            switching->setText("Switch status: " + detail);
            rxPower->setText("RX power: " + rx);
        }
    };
    auto update = [&]() {
        render();
        if (pending) return;
        pending = true;
        auto msg = QDBusMessage::createMethodCall("org.kde.KWin", "/Compositor", "org.freedesktop.DBus.Properties", "Get");
        msg << "org.kde.kwin.Compositing" << "primaryGpu";
        auto *watcher = new QDBusPendingCallWatcher(QDBusConnection::sessionBus().asyncCall(msg, 1200), &app);
        QObject::connect(watcher, &QDBusPendingCallWatcher::finished, &app, [&, watcher]() {
            QDBusPendingReply<QDBusVariant> reply = *watcher;
            queried = true; pending = false;
            dbusError = reply.isError() ? reply.error().message() : QString();
            currentNode = reply.isError() ? QString() : reply.value().variant().toString();
            watcher->deleteLater(); render();
        });
    };
    QObject::connect(refresh, &QAction::triggered, &app, update);
    QObject::connect(&tray, &QSystemTrayIcon::activated, &app, [&](QSystemTrayIcon::ActivationReason reason) {
        if (reason == QSystemTrayIcon::Trigger) { update(); menu.popup(QCursor::pos()); }
    });
    QTimer timer;
    QObject::connect(&timer, &QTimer::timeout, &app, update);
    timer.start(2000); update(); tray.show();
    return app.exec();
}
