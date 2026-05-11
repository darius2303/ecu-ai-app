import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://127.0.0.1:8000';

  Future<Map<String, dynamic>> analyze(Map<String, dynamic> inputData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(inputData),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Analyze failed: ${response.statusCode} ${response.body}');
  }

  Future<Map<String, dynamic>> fuelMap(Map<String, dynamic> inputData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/fuel-map'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(inputData),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Fuel map failed: ${response.statusCode} ${response.body}');
  }

  Future<Uint8List> fuelMapImage(Map<String, dynamic> inputData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/fuel-map-image'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(inputData),
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    }
    throw Exception('Fuel map image failed: ${response.statusCode}');
  }

  Future<Uint8List> report(Map<String, dynamic> inputData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/report'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(inputData),
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    }
    throw Exception('Report generation failed: ${response.statusCode}');
  }
}
