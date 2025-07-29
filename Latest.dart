import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';
import 'package:firebase_database/firebase_database.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

// ...

void main() async {
  WidgetsFlutterBinding.ensureInitialized();  // Required for async main
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  runApp(const SmartPickApp());

  FirebaseDatabase database = FirebaseDatabase.instance;
  FirebaseApp secondaryApp = Firebase.app('SecondaryApp');
  final firebaseApp = Firebase.app();
  final rtdb = FirebaseDatabase.instanceFor(app: firebaseApp, databaseURL: 'https://your-realtime-database-url.firebaseio.com/');
}

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});
  Map<String, dynamic>? doorAlert;

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  final DatabaseReference _dbRef = FirebaseDatabase.instance.ref().child('Deliveries/');
  List<Parcel> _parcels = [];

  @override
  void initState() {
    super.initState();
    fetchDoorAlertStatus();
    Timer.periodic(const Duration(seconds: 15), (timer) {
      fetchDoorAlertStatus();
    });
  }

  void _fetchParcels() async{
    final snapshot = await _dbRef.get();
    final parcels = <Parcel>[];

    if(snapshot.exists) {
      final data = snapshot.value as Map<dynamic, dynamic>;
      data.forEach((key, value) {
        parcels.add(Parcel.fromMap(key, value));
      });
    }

    setState(() {
      _parcels = parcels;
    });
  }

  Future<void> fetchDoorAlertStatus() async {
  try {
    final response = await http.get(Uri.parse('http://10.189.197.148:5000/door-status'));
    if (response.statusCode == 200) {
      final jsonData = jsonDecode(response.body);
      setState(() {
        doorAlert = jsonData['door_alert'];
      });
    } else {
      print('Failed to load alert status');
    }
  } catch (e) {
    print('Error fetching alert: $e');
  }
}


  void _markCollected(int index) async {
    final parcel = _parcels[index];
    final parcelId = parcel.id;

    await FirebaseDatabase.instance.ref('Deliveries/$parcelId').update({
      'status': 'Collected',
    });

    setState(() {
      _parcels[index] = Parcel(
        id: parcel.id,
        locker: parcel.locker,
        pin: parcel.pin,
        status: 'Collected',
      );
    });

    // setState(() {
    //   parcels[index]['status'] = 'Collected';
    // });
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
            onPressed: () async {
              if (id.isNotEmpty && locker.isNotEmpty && pin.isNotEmpty) {
                await FirebaseDatabase.instance.ref('Deliveries/$id').set({
                  'locker': locker,
                  'pin': int.tryParse(pin) ?? 0,
                  'status': 'Ready for Pickup',
                });

                // Optional: Refresh UI by re-fetching data
                _fetchParcels();
                Navigator.pop(context);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Dashboard')),
      if (doorAlert != null) ...[
        Container(
          padding: const EdgeInsets.all(12),
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.red[100],
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              const Icon(Icons.warning, color: Colors.red),
              const SizedBox(width: 8),
              Expanded(child: Text(doorAlert!['alert'] ?? "Unknown Alert")),
            ],
          ),
        )
      ],
      body: ListView.builder(
        itemCount: _parcels.length,
        padding: const EdgeInsets.all(16),
        itemBuilder: (context, index) {
          final parcel = _parcels[index];
          return Card(
            margin: const EdgeInsets.symmetric(vertical: 8),
            child: ListTile(
              leading: const Icon(Icons.inventory),
              title: Text('Parcel ID: ${parcel.id}'),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  Text('Locker: ${parcel.locker}'),
                  Text('PIN: ${parcel.pin}'),
                  Text('Status: ${parcel.status}'),
                ],
              ),
              trailing: parcel.status == 'Ready for Pickup'
                  ? IconButton(
                icon: const Icon(Icons.check_circle, color: Colors.green),
                onPressed: () => _markCollected(index),
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

class Parcel {
  final String id;
  final String locker;
  final int pin;
  final String status;

  Parcel({required this.id, required this.locker, required this.pin, required this.status});

  factory Parcel.fromMap(String id, Map<dynamic, dynamic> data) {
    return Parcel(
      id: id,
      locker: data['locker'],
      pin: data['pin'],
      status: data['status'],

    );
  }
}

class SmartPickApp extends StatelessWidget {
  const SmartPickApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartPick App',
      home: Scaffold(
        body: HomeScreen(),
      ),
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
        '/Homescreen': (context) => const HomeScreen(),
        // '/parcelinfo': (context) => const ParcelInfoScreen(),
        '/collectparcel': (context) => const CollectParcelScreen(),
        '/about': (context) => const AboutScreen(),
        '/face': (context) => const FacialRecognitionScreen(),
        '/notifications': (context) => const NotificationScreen(),
        '/admin_login': (context) => const AdminLoginScreen(),
        '/admin_dashboard': (context) => const AdminDashboardScreen(),
      },
      onGenerateRoute: (settings) {
        if (settings.name == '/parcelinfo') {
          final parcel = settings.arguments as Parcel;
          return MaterialPageRoute(
            builder: (context) => ParcelInfoScreen(parcel: parcel),
          );
        }

        // Optional fallback:
        return MaterialPageRoute(
          builder: (context) => const Scaffold(
            body: Center(child: Text('Page not found')),
          ),
        );
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
                    onTap: () => Navigator.pushNamed(context, '/collectparcel'),
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
  final Parcel parcel;

  const ParcelInfoScreen({Key? key, required this.parcel}) : super(key: key);

  @override
  State<ParcelInfoScreen> createState() => _ParcelInfoScreenState();
  // const ParcelInfoScreen({super.key});
  // @override
  // State<ParcelInfoScreen> createState() => _ParcelInfoScreenState();
}

class _ParcelInfoScreenState extends State<ParcelInfoScreen> {
  final _PINController = TextEditingController();
  // String _pin = '';
  // final String lockerLocation = "Row D - Locker 47";
  // String status = "Ready for Pickup";
  bool _isPinVisible = false;

  @override
  void initState() {
    super.initState();
  }

  void _enterPIN() async {
    final enteredPIN = _PINController.text.trim();
    final enteredPin_Int = int.tryParse(enteredPIN);
    final storedPIN = widget.parcel.pin;

    // final snapshot = await FirebaseDatabase.instance.ref('Admin').get();
    if (storedPIN == enteredPin_Int) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Correct PIN entered.')),
      );
      await _updateParcelStatus(widget.parcel.id, "Unlocked");
      await _unlockLocker(widget.parcel.id);
      // Navigator.pushReplacementNamed(context, '/admin_dashboard'); //placeholder for now
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invalid PIN!')),
      );
    }
  }

  Future<void> _updateParcelStatus(String parcelId, String newStatus) async {
    final ref = FirebaseDatabase.instance.ref('Deliveries/$parcelId');
    await ref.update({'status': newStatus});
  }


  Future<void> _unlockLocker(String parcel_id) async {
    const String raspberryPiIP = 'http://192.168.1.32:5000'; // <-- Replace with your actual Pi IP

    final url = Uri.parse('$raspberryPiIP/unlock_locker');

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'parcel_id': parcel_id,
          // 'pin': pin
        }),
      );

      if (response.statusCode == 200) {
        print('Locker door has been opened: $parcel_id');
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('PIN sent to Smart Locker')),
        );
      } else {
        print('Failed to send PIN. Status: ${response.statusCode}');
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to send PIN to Pi')),
        );
      }
    } catch (e) {
      print('Error sending PIN: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context); // Added this line to fix the error

    return Scaffold(
      appBar: AppBar(
        title: const Text('Parcel Information'),
      ),
      // drawer: const AppDrawer(),
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
                            Icons.account_box_rounded,
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
                                'Parcel ID',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  color: Colors.grey[600],
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${widget.parcel.id}',
                                style: theme.textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w600,
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
                                '${widget.parcel.status}',
                                style: theme.textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w600,
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
                                // lockerLocation,
                                '${widget.parcel.locker}',
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
                              TextField(
                                controller: _PINController,
                                decoration: const InputDecoration(labelText: 'Enter PIN'),
                              ),
                              const SizedBox(height: 24),
                            ],
                          ),
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
                        icon: const Icon(Icons.arrow_forward_rounded, size: 20),
                        label: const Text('Confirm PIN'),
                        onPressed: _enterPIN,
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
                onPressed: () => Navigator.pushNamed(context, '/Homescreen'),
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

class CollectParcelScreen extends StatefulWidget {
  const CollectParcelScreen({super.key});

  @override
  State<CollectParcelScreen> createState() => _CollectParcelScreenState();
}

class _CollectParcelScreenState extends State<CollectParcelScreen> {
  final DatabaseReference _dbRef = FirebaseDatabase.instance.ref().child('Deliveries/');
  List<Parcel> _parcels = [];

  @override
  void initState() {
    super.initState();
    _fetchParcels();
  }
  void _fetchParcels() async{
    final snapshot = await _dbRef.get();
    final parcels = <Parcel>[];

    if(snapshot.exists) {
      final data = snapshot.value as Map<dynamic, dynamic>;
      data.forEach((key, value) {
        final parcel = Parcel.fromMap(key, value);
        if (parcel.status == 'Ready for Pickup') {
          parcels.add(parcel);
        }
      // final data = snapshot.value as Map<dynamic, dynamic>;
      // data.forEach((key, value) {
      //   parcels.add(Parcel.fromMap(key, value));
      });
    }

    setState(() {
      _parcels = parcels;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Choose your parcel')),
      body: ListView.builder(
        itemCount: _parcels.length,
        padding: const EdgeInsets.all(16),
        itemBuilder: (context, index) {
          final parcel = _parcels[index];
          return Card(
            margin: const EdgeInsets.symmetric(vertical: 8),
            child: ListTile(
              leading: const Icon(Icons.inventory),
              title: Text('Parcel ID: ${parcel.id}'),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Locker: ${parcel.locker}'),
                  // Text('PIN: ${parcel.pin}'),
                  Text('Status: ${parcel.status}'),
                ],
              ),
              trailing: parcel.status == 'Ready for Pickup'
                  ? IconButton(
                icon: const Icon(Icons.check_circle, color: Colors.green),
                  // onPressed: () => Navigator.pushNamed(context, '/parcelinfo'),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => ParcelInfoScreen(parcel: parcel),
                    ),
                  );
                },
              )
                  : const Icon(Icons.done, color: Colors.grey),
            ),
          );
        },
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

  void _login() async {
    final enteredUsername = _usernameController.text.trim();
    final enteredPassword = _passwordController.text.trim();
    final snapshot = await FirebaseDatabase.instance.ref('Admin').get();

    if (snapshot.exists) {
      final data = snapshot.value as Map<dynamic, dynamic>;
      final storedUsername = data['username'];
      final storedPassword = data['password'];

      if(enteredUsername == storedUsername && enteredPassword == storedPassword) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Login successful')),
        );
        Navigator.pushReplacementNamed(context, '/admin_dashboard');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Invalid username or password!')),
        );
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Admin data not found')),
      );
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
                onPressed: () => Navigator.pushNamed(context, '/'),
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

class FacialRecognitionScreen extends StatelessWidget {
  const FacialRecognitionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Facial Recognition'),
      ),
      drawer: const AppDrawer(),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.face_retouching_natural, size: 100, color: Colors.deepPurple),
              const SizedBox(height: 30),
              const Text(
                'Facial Recognition Coming Soon!',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 20),
              const Text(
                'This feature will let you authenticate securely using face detection.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 40),
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
              Navigator.pushNamed(context, '/collectparcel');
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