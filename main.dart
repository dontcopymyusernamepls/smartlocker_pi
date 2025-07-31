import 'dart:math';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:async';
import 'package:camera/camera.dart';


Timer? _reconnectTimer;
int _reconnectAttempts = 0;
const int _maxReconnectAttempts = 5;
const Duration _reconnectDelay = Duration(seconds: 3);

void main() {
  runApp(const SmartPickApp());
}

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  List<Map<String, dynamic>> parcels = [
    {
      'id': 'P001',
      'locker': 'Row D - Locker 47',
      'status': 'Ready for Pickup',
      'pin': '689950'
    },
    {
      'id': 'P002',
      'locker': 'Row B - Locker 10',
      'status': 'Collected',
      'pin': '123456'
    },
  ];

  // Sensor data
  double? temperature;
  double? humidity;
  bool? isLockerEmpty;
  String? parcelOverdueMessage;
  String? errorMessage;
  String? lockerEmptyStatus;

  // Connection state
  bool isLoading = true;
  bool alertShown = false;
  String? connectionError;
  late WebSocketChannel _channel;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const _maxReconnectAttempts = 5;
  static const _reconnectDelay = Duration(seconds: 3);

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  @override
  void dispose() {
    _channel.sink.close();
    _reconnectTimer?.cancel();
    super.dispose();
  }

  void _connectWebSocket() {
    setState(() {
      isLoading = true;
      connectionError = null;
    });

    try {
      _channel = WebSocketChannel.connect(Uri.parse('ws://192.168.158.163:8765'));

      _channel.stream.listen(
        _handleWebSocketMessage,
        onError: _handleWebSocketError,
        onDone: _handleWebSocketDisconnect,
      );
    } catch (e) {
      _handleConnectionError(e);
    }
  }

  void _handleWebSocketMessage(dynamic message) {
    try {
      final data = jsonDecode(message);
      print('Received WebSocket data: $data'); // Debug log

      setState(() {
        // Handle temperature/humidity data
        if (data['temperature'] != null) {
          temperature = data['temperature']?.toDouble();
          humidity = data['humidity']?.toDouble();
          print('Updated temperature: $temperature, humidity: $humidity');
        }

        // Handle IR sensor data
        if (data['locker_empty'] != null) {
          lockerEmptyStatus = data['locker_empty'].toString();
          isLockerEmpty = lockerEmptyStatus == "Yes";

          // Reset alertShown when locker becomes empty
          if (isLockerEmpty!) {
            alertShown = false;
          }

          // Handle parcel overdue message
          if (data['message'] != null) {
            parcelOverdueMessage = data['message'].toString();

            if (parcelOverdueMessage!.isNotEmpty && !isLockerEmpty! && !alertShown) {
              _showAlertMessage(parcelOverdueMessage!);
              alertShown = true;
            }
          } else {
            parcelOverdueMessage = null;
          }

          print('Updated locker status: $lockerEmptyStatus, message: $parcelOverdueMessage');
        }

        isLoading = false;
      });
    } catch (e) {
      print('Error parsing WebSocket message: $e');
      setState(() {
        errorMessage = 'Data parsing error: $e';
        isLoading = false;
      });
    }
  }


  void _showAlertMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _handleWebSocketError(error) {
    setState(() {
      connectionError = 'Connection error: $error';
      isLoading = false;
    });
    _scheduleReconnect();
  }

  void _handleWebSocketDisconnect() {
    setState(() {
      connectionError = 'Connection lost. Reconnecting...';
      isLoading = false;
    });
    _scheduleReconnect();
  }

  void _handleConnectionError(e) {
    setState(() {
      connectionError = 'Failed to connect: $e';
      isLoading = false;
    });
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _reconnectTimer = Timer(_reconnectDelay, () {
        _reconnectAttempts++;
        _connectWebSocket();
      });
    } else {
      setState(() {
        connectionError = 'Max reconnect attempts reached';
      });
    }
  }

  Widget _buildLockerStatusIndicator() {
    if (isLockerEmpty == null) return const Text('Status: Unknown');

    return Row(
      children: [
        Icon(
          isLockerEmpty! ? Icons.check_circle : Icons.error,
          color: isLockerEmpty! ? Colors.green : Colors.orange,
        ),
        const SizedBox(width: 8),
        Text(
          isLockerEmpty! ? 'Locker Empty' : 'Locker Occupied',
          style: TextStyle(
            color: isLockerEmpty! ? Colors.green : Colors.orange,
          ),
        ),
      ],
    );
  }

  Widget _buildConnectionStatus() {
    if (connectionError != null) {
      return Row(
        children: [
          const Icon(Icons.wifi_off, color: Colors.red),
          const SizedBox(width: 8),
          Expanded(child: Text(connectionError!)),
        ],
      );
    }
    return Row(
      children: [
        const Icon(Icons.wifi, color: Colors.green),
        const SizedBox(width: 8),
        const Text('Connected'),
      ],
    );
  }

  void _markCollected(int index) {
    setState(() {
      parcels[index]['status'] = 'Collected';
    });
  }

  void _showAddParcelDialog() {
    String id = '';
    String locker = '';
    String pin = '';

    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Add New Parcel'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              onChanged: (val) => id = val,
              decoration: const InputDecoration(labelText: 'Parcel ID'),
            ),
            TextField(
              onChanged: (val) => locker = val,
              decoration: const InputDecoration(labelText: 'Locker Location'),
            ),
            TextField(
              onChanged: (val) => pin = val,
              decoration: const InputDecoration(labelText: 'Pickup PIN'),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (id.isNotEmpty && locker.isNotEmpty && pin.isNotEmpty) {
                setState(() {
                  parcels.add({
                    'id': id,
                    'locker': locker,
                    'pin': pin,
                    'status': 'Ready for Pickup',
                  });
                });
                Navigator.pop(context);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  Widget buildLockerStatistics() {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (errorMessage != null) {
      return Text(errorMessage!, style: const TextStyle(color: Colors.red));
    }

    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Locker Statistics',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                const Icon(Icons.thermostat, color: Colors.deepOrange),
                const SizedBox(width: 10),
                Text('Temperature: ${temperature?.toStringAsFixed(1) ?? '-'} °C'),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.water_drop, color: Colors.blue),
                const SizedBox(width: 10),
                Text('Humidity: ${humidity?.toStringAsFixed(1) ?? '-'} %'),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.inventory, color: Colors.purple),
                const SizedBox(width: 10),
                Text('Locker Empty: ${lockerEmptyStatus ?? '-'}'),
              ],
            ),
            if (parcelOverdueMessage != null && parcelOverdueMessage!.isNotEmpty) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  const Icon(Icons.error_outline, color: Colors.red),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      parcelOverdueMessage!,
                      style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Dashboard')),
      body: ListView.builder(
        itemCount: parcels.length + 1,
        padding: const EdgeInsets.all(16),
        itemBuilder: (context, index) {
          if (index == 0) {
            return buildLockerStatistics();
          }

          final parcel = parcels[index - 1];
          return Card(
            margin: const EdgeInsets.symmetric(vertical: 8),
            child: ListTile(
              leading: const Icon(Icons.inventory),
              title: Text('Parcel ID: ${parcel['id']}'),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Locker: ${parcel['locker']}'),
                  Text('PIN: ${parcel['pin']}'),
                  Text('Status: ${parcel['status']}'),
                ],
              ),
              trailing: parcel['status'] == 'Ready for Pickup'
                  ? IconButton(
                icon: const Icon(Icons.check_circle, color: Colors.green),
                onPressed: () => _markCollected(index - 1),
              )
                  : const Icon(Icons.done, color: Colors.grey),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddParcelDialog,
        child: const Icon(Icons.add),
        tooltip: 'Add Parcel',
      ),
    );
  }
}




class SmartPickApp extends StatelessWidget {
  const SmartPickApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartPick App',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF6C56F5)),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF8F9FB),
        textTheme: GoogleFonts.poppinsTextTheme(
          Theme.of(context).textTheme,
        ),
        appBarTheme: AppBarTheme(
          centerTitle: true,
          elevation: 0,
          backgroundColor: const Color(0xFF6C56F5), // Purple background
          titleTextStyle: GoogleFonts.poppins(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: Colors.white, // White text
          ),
        ),
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => const HomeScreen(),
        '/parcelinfo': (context) => const ParcelInfoScreen(),
        '/about': (context) => const AboutScreen(),
        '/face': (context) => const FacialRecognitionScreen(),
        '/notifications': (context) => const NotificationScreen(),
        '/admin_login': (context) => const AdminLoginScreen(),
        '/admin_dashboard': (context) => const AdminDashboardScreen(),

      },
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('SmartPick'),
        actions: [
          IconButton(
            icon: Badge(
              smallSize: 8,
              child: const Icon(Icons.notifications_outlined),
            ),
            onPressed: () => Navigator.pushNamed(context, '/notifications'),
          ),
        ],
      ),
      drawer: const AppDrawer(),
      body: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Welcome to SmartPick',
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'Secure. Smart. Seamless Parcel Pickup.',
              style: theme.textTheme.titleMedium?.copyWith(
                color: Colors.grey[700],
              ),
            ),
            const SizedBox(height: 40),
            Expanded(
              child: ListView(
                children: [
                  _HomeCardButton(
                    icon: Icons.local_shipping_outlined,
                    title: 'Pickup Your Parcel',
                    description: 'View locker location and pickup PIN',
                    color: const Color(0xFF6C56F5),
                    onTap: () => Navigator.pushNamed(context, '/parcelinfo'),
                  ),
                  const SizedBox(height: 16),
                  _HomeCardButton(
                    icon: Icons.face_retouching_natural,
                    title: 'Facial Recognition',
                    description: 'Use face ID for secure locker access',
                    color: const Color(0xFF00C9A7),
                    onTap: () => Navigator.pushNamed(context, '/face'),
                  ),
                  const SizedBox(height: 16),
                  _HomeCardButton(
                    icon: Icons.info_outline,
                    title: 'About SmartPick',
                    description: 'Learn how this system works',
                    color: const Color(0xFF845EC2),
                    onTap: () => Navigator.pushNamed(context, '/about'),
                  ),

                  _HomeCardButton(
                    icon: Icons.admin_panel_settings,
                    title: 'Admin Login',
                    description: 'Manage parcels and locker status',
                    color: Colors.deepPurple,
                    onTap: () => Navigator.pushNamed(context, '/admin_login'),
                  ),

                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ParcelInfoScreen extends StatefulWidget {
  const ParcelInfoScreen({super.key});

  @override
  State<ParcelInfoScreen> createState() => _ParcelInfoScreenState();
}

class _ParcelInfoScreenState extends State<ParcelInfoScreen> {
  String _pin = '';
  final String lockerLocation = "Row D - Locker 47";
  String status = "Ready for Pickup";
  bool _isPinVisible = false;
  late WebSocketChannel _pinChannel;

  @override
  void initState() {
    super.initState();
    _connectPinWebSocket();
    _generatePin();
  }

  void _connectPinWebSocket() {
    const String pinWsUrl = 'ws://192.168.158.163:8765';

    // Cancel any pending reconnection attempts
    _reconnectTimer?.cancel();

    try {
      _pinChannel = WebSocketChannel.connect(Uri.parse(pinWsUrl));
      _reconnectAttempts = 0; // Reset counter on successful connection

      // Listen for connection state changes
      _pinChannel.stream.listen(
            (message) {
          // Handle incoming messages if needed
          print('Received: $message');
        },
        onError: (error) {
          print('WebSocket error: $error');
          _handleDisconnection();
        },
        onDone: () {
          print('WebSocket disconnected');
          _handleDisconnection();
        },
        cancelOnError: true,
      );

      print('PIN WebSocket connected successfully');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Connected to Smart Locker')),
      );
    } catch (e) {
      print('PIN WebSocket connection error: $e');
      _handleDisconnection();
    }
  }

  void _handleDisconnection() {
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _reconnectAttempts++;
      print('Attempting to reconnect ($_reconnectAttempts/$_maxReconnectAttempts)...');

      _reconnectTimer = Timer(_reconnectDelay, () {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Reconnecting... ($_reconnectAttempts/$_maxReconnectAttempts)'),
            duration: _reconnectDelay,
          ),
        );
        _connectPinWebSocket();
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Connection failed. Please check network and try again.'),
          duration: Duration(seconds: 5),
        ),
      );
    }
  }

  Future<void> _sendPinToPi(String pin) async {
    try {
      _pinChannel.sink.add(jsonEncode({'pin': pin}));
      print('PIN sent successfully: $pin');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('PIN sent to Smart Locker')),
      );
    } catch (e) {
      print('Failed to send PIN: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to send PIN: $e')),
      );
      // Attempt to reconnect
      _connectPinWebSocket();
    }
  }

  void _generatePin() {
    final random = Random();
    final newPin = (100000 + random.nextInt(900000)).toString();
    setState(() {
      _pin = newPin;
      _isPinVisible = false;
    });
    _sendPinToPi(newPin);
  }

  void _togglePinVisibility() {
    setState(() {
      _isPinVisible = !_isPinVisible;
    });
  }

  @override
  void dispose() {
    _pinChannel.sink.close();
    _reconnectTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context); // Added this line to fix the error

    return Scaffold(
      appBar: AppBar(
        title: const Text('Parcel Information'),
      ),
      drawer: const AppDrawer(),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF6C56F5).withOpacity(0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.local_shipping_outlined,
                            color: Color(0xFF6C56F5),
                            size: 28,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Parcel Status',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  color: Colors.grey[600],
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                status,
                                style: theme.textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: status == "Collected"
                                      ? Colors.green
                                      : const Color(0xFF6C56F5),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    const Divider(height: 1),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF00C9A7).withOpacity(0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.place_outlined,
                            color: Color(0xFF00C9A7),
                            size: 28,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Locker Location',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  color: Colors.grey[600],
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                lockerLocation,
                                style: theme.textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),

            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFF8066).withOpacity(0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.lock_outline,
                            color: Color(0xFFFF8066),
                            size: 28,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Pickup PIN',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  color: Colors.grey[600],
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                _isPinVisible ? _pin : '••••••',
                                style: theme.textTheme.headlineSmall?.copyWith(
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 4,
                                  color: const Color(0xFF6C56F5),
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: Icon(
                            _isPinVisible
                                ? Icons.visibility_off
                                : Icons.visibility,
                            color: Colors.grey,
                          ),
                          onPressed: _togglePinVisibility,
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF6C56F5),
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        icon: const Icon(Icons.refresh, size: 20),
                        label: const Text('Generate New PIN'),
                        onPressed: _generatePin,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.home),
                label: const Text('Back to Home'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  backgroundColor: const Color(0xFF6C56F5),
                  foregroundColor: Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class AdminLoginScreen extends StatefulWidget {
  const AdminLoginScreen({super.key});

  @override
  State<AdminLoginScreen> createState() => _AdminLoginScreenState();
}

class _AdminLoginScreenState extends State<AdminLoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  String? _errorText;

  void _login() {
    if (_usernameController.text == 'admin' &&
        _passwordController.text == 'admin123') {
      Navigator.pushReplacementNamed(context, '/admin_dashboard');
    } else {
      setState(() => _errorText = 'Invalid username or password');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Login')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _usernameController,
              decoration: const InputDecoration(labelText: 'Username'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordController,
              decoration: const InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
            if (_errorText != null) ...[
              const SizedBox(height: 8),
              Text(_errorText!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _login,
              child: const Text('Login'),
            ),
          ],
        ),
      ),
    );
  }
}


class NotificationScreen extends StatelessWidget {
  const NotificationScreen({super.key});

  final List<Map<String, String>> notifications = const [
    {
      "title": "Parcel Delivered to Locker",
      "body": "Your parcel has been placed at Row D - Locker 47.",
      "time": "Today, 10:45 AM",
      "status": "Ready for Pickup"
    },
    {
      "title": "Pickup PIN Generated",
      "body": "Your 6-digit PIN is 839201.",
      "time": "Today, 10:46 AM",
      "status": "Ready for Pickup"
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
      ),
      drawer: const AppDrawer(),
      body: Column(
        children: [
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: notifications.length,
              separatorBuilder: (_, __) => const Divider(),
              itemBuilder: (context, index) {
                final notification = notifications[index];
                return ListTile(
                  leading: const Icon(Icons.notifications_active, size: 32),
                  title: Text(notification["title"] ?? ''),
                  subtitle: Text(notification["body"] ?? ''),
                  trailing: Text(notification["time"] ?? ''),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.home),
                label: const Text('Back to Home'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  backgroundColor: const Color(0xFF6C56F5),
                  foregroundColor: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('About SmartPick'),
      ),
      drawer: const AppDrawer(),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  color: const Color(0xFF6C56F5).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(24),
                ),
                child: const Icon(
                  Icons.smart_toy_outlined,
                  size: 60,
                  color: Color(0xFF6C56F5),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'About SmartPick',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'SmartPick revolutionizes parcel collection with cutting-edge technology for a seamless, secure experience.',
              style: TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 32),

            // Feature Tiles
            Text(
              'Key Features',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            const FeatureTile(
              icon: Icons.face_retouching_natural,
              title: 'Facial Recognition',
              description: 'Biometric authentication for secure access',
              color: Color(0xFF00C9A7),
            ),
            const FeatureTile(
              icon: Icons.lock_outline,
              title: 'PIN Protection',
              description: 'One-time codes for each delivery',
              color: Color(0xFFFF8066),
            ),
            const FeatureTile(
              icon: Icons.notifications_active_outlined,
              title: 'Real-time Alerts',
              description: 'Instant updates on your deliveries',
              color: Color(0xFF845EC2),
            ),
            //const FeatureTile(
            // icon: Icons.security,
            //title: 'Secure Storage',
            // description: 'Tamper-proof lockers for your parcels',
            // color: Color(0xFF6C56F5),
            //),

            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.home),
                label: const Text('Back to Home'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  backgroundColor: const Color(0xFF6C56F5),
                  foregroundColor: Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class FacialRecognitionScreen extends StatefulWidget {
  const FacialRecognitionScreen({super.key});

  @override
  State<FacialRecognitionScreen> createState() => _FacialRecognitionScreenState();
}

class _FacialRecognitionScreenState extends State<FacialRecognitionScreen> {
  CameraController? _cameraController;
  late List<CameraDescription> _cameras;
  bool _isProcessing = false;
  String _statusMessage = 'Point camera to your face and tap "Scan & Unlock"';

  late WebSocketChannel _faceChannel;

  @override
  void initState() {
    super.initState();
    _initCamera();
    _connectFaceWebSocket();  // Connect WS on init
  }

  Future<void> _initCamera() async {
    _cameras = await availableCameras();
    _cameraController = CameraController(_cameras[1], ResolutionPreset.medium);
    await _cameraController!.initialize();
    if (mounted) setState(() {});
  }

  void _connectFaceWebSocket() {
    const String faceWsUrl = 'ws://192.168.158.163:8765';
    _faceChannel = WebSocketChannel.connect(Uri.parse(faceWsUrl));

    _faceChannel.stream.listen(
      _handleFaceWebSocketMessage,
      onError: _handleFaceWebSocketError,
      onDone: _handleFaceWebSocketDisconnect,
    );
  }

  void _handleFaceWebSocketMessage(dynamic message) {
    try {
      final decoded = jsonDecode(message);
      if (decoded['type'] == 'face_auth_response') {
        setState(() {
          _statusMessage = decoded['success']
              ? 'Face recognized. Locker unlocked!'
              : 'Face not recognized or unauthorized.';
          _isProcessing = false;
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = 'Invalid response from server.';
        _isProcessing = false;
      });
    }
  }

  void _handleFaceWebSocketError(error) {
    setState(() {
      _statusMessage = 'WebSocket error: $error';
      _isProcessing = false;
    });
  }

  void _handleFaceWebSocketDisconnect() {
    setState(() {
      _statusMessage = 'WebSocket connection closed.';
      _isProcessing = false;
    });
  }

  Future<void> _captureAndSendImage() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    setState(() {
      _isProcessing = true;
      _statusMessage = 'Scanning...';
    });

    try {
      final XFile photo = await _cameraController!.takePicture();
      final bytes = await photo.readAsBytes();
      final base64Image = base64Encode(bytes);

      final payload = jsonEncode({
        "type": "face_auth",
        "image": base64Image,
      });

      _faceChannel.sink.add(payload);
      // Wait for server response in _handleFaceWebSocketMessage
    } catch (e) {
      setState(() {
        _statusMessage = 'Error: ${e.toString()}';
        _isProcessing = false;
      });
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _faceChannel.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Facial Recognition')),
      body: Column(
        children: [
          if (_cameraController != null && _cameraController!.value.isInitialized)
            AspectRatio(
              aspectRatio: _cameraController!.value.aspectRatio,
              child: CameraPreview(_cameraController!),
            )
          else
            const Center(child: CircularProgressIndicator()),
          const SizedBox(height: 20),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              _statusMessage,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16),
            ),
          ),
          if (!_isProcessing)
            ElevatedButton.icon(
              onPressed: _captureAndSendImage,
              icon: const Icon(Icons.lock_open),
              label: const Text('Scan & Unlock'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 32),
                backgroundColor: Colors.deepPurple,
                foregroundColor: Colors.white,
              ),
            ),
        ],
      ),
    );
  }
}


class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          const DrawerHeader(
            decoration: BoxDecoration(
              color: Color(0xFF6C56F5),
            ),
            child: Text(
              'SmartPick Menu',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
              ),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.home),
            title: const Text('Home'),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushNamed(context, '/');
            },
          ),
          ListTile(
            leading: const Icon(Icons.lock),
            title: const Text('Pickup Parcel'),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushNamed(context, '/parcelinfo');
            },
          ),
          ListTile(
            leading: const Icon(Icons.face),
            title: const Text('Facial Recognition'),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushNamed(context, '/face');
            },
          ),
          ListTile(
            leading: const Icon(Icons.info),
            title: const Text('About'),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushNamed(context, '/about');
            },
          ),
        ],
      ),
    );
  }
}

class _HomeCardButton extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;
  final Color color;
  final VoidCallback onTap;

  const _HomeCardButton({
    required this.icon,
    required this.title,
    required this.description,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: color, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.grey),
            ],
          ),
        ),
      ),
    );
  }
}

class FeatureTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;
  final Color color;

  const FeatureTile({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
