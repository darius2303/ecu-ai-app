import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://127.0.0.1:8000';

  Future<Map<String, dynamic>> analyzeCalibration({
    required String originalFileName,
    required Uint8List originalBytes,
    String? modifiedFileName,
    Uint8List? modifiedBytes,
    String? definitionsFileName,
    Uint8List? definitionsBytes,
    double? engineDisplacement,
    required String fuelType,
    required bool isTurbo,
    double? stockHp,
  }) async {
    final body = <String, dynamic>{
      'original_file': {
        'file_name': originalFileName,
        'content_base64': base64Encode(originalBytes),
      },
      'engine_displacement': engineDisplacement,
      'fuel_type': fuelType,
      'is_turbo': isTurbo,
      'stock_hp': stockHp,
    };

    if (modifiedFileName != null && modifiedBytes != null) {
      body['modified_file'] = {
        'file_name': modifiedFileName,
        'content_base64': base64Encode(modifiedBytes),
      };
    }
    if (definitionsFileName != null && definitionsBytes != null) {
      body['definitions_file'] = {
        'file_name': definitionsFileName,
        'content_base64': base64Encode(definitionsBytes),
      };
    }

    final response = await http.post(
      Uri.parse('$baseUrl/api/calibration/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
      'Calibration analyze failed: ${response.statusCode} ${response.body}',
    );
  }

  Future<Map<String, dynamic>> parseMapFile({
    required String fileName,
    required Uint8List bytes,
    required String mapType,
    required String fuelType,
    required bool isTurbo,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/parse-map-file'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'file_name': fileName,
        'content_base64': base64Encode(bytes),
        'map_type': mapType,
        'fuel_type': fuelType,
        'is_turbo': isTurbo,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
      'Map import failed: ${response.statusCode} ${response.body}',
    );
  }

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
