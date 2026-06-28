import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

/// Clientul HTTP folosit de interfata pentru comunicarea cu backend-ul local.
class ApiService {
  static const String baseUrl = 'http://127.0.0.1:8000';

  /// Construieste payload-ul comun pentru analiza, raport si exporturi.
  Map<String, dynamic> _calibrationBody({
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
  }) {
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

    return body;
  }

  /// Trimite fisierele ECU catre backend si returneaza rezultatul analizei.
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
    final body = _calibrationBody(
      originalFileName: originalFileName,
      originalBytes: originalBytes,
      modifiedFileName: modifiedFileName,
      modifiedBytes: modifiedBytes,
      definitionsFileName: definitionsFileName,
      definitionsBytes: definitionsBytes,
      engineDisplacement: engineDisplacement,
      fuelType: fuelType,
      isTurbo: isTurbo,
      stockHp: stockHp,
    );

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

  /// Cere backend-ului sa genereze raportul PDF si intoarce bytes-ii fisierului.
  Future<Uint8List> calibrationReport({
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
    final body = _calibrationBody(
      originalFileName: originalFileName,
      originalBytes: originalBytes,
      modifiedFileName: modifiedFileName,
      modifiedBytes: modifiedBytes,
      definitionsFileName: definitionsFileName,
      definitionsBytes: definitionsBytes,
      engineDisplacement: engineDisplacement,
      fuelType: fuelType,
      isTurbo: isTurbo,
      stockHp: stockHp,
    );

    final response = await http.post(
      Uri.parse('$baseUrl/api/calibration/report'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    }
    throw Exception(
      'Calibration report failed: ${response.statusCode} ${response.body}',
    );
  }

  /// Exporta datasetul JSON folosit pentru experimente si etichetare ML.
  Future<Uint8List> calibrationMlDataset({
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
    final body = _calibrationBody(
      originalFileName: originalFileName,
      originalBytes: originalBytes,
      modifiedFileName: modifiedFileName,
      modifiedBytes: modifiedBytes,
      definitionsFileName: definitionsFileName,
      definitionsBytes: definitionsBytes,
      engineDisplacement: engineDisplacement,
      fuelType: fuelType,
      isTurbo: isTurbo,
      stockHp: stockHp,
    );

    final response = await http.post(
      Uri.parse('$baseUrl/api/calibration/ml-dataset'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    }
    throw Exception(
      'ML dataset export failed: ${response.statusCode} ${response.body}',
    );
  }

  /// Exporta template-ul CSV care poate fi completat manual pentru training.
  Future<Uint8List> calibrationLabelingTemplate({
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
    final body = _calibrationBody(
      originalFileName: originalFileName,
      originalBytes: originalBytes,
      modifiedFileName: modifiedFileName,
      modifiedBytes: modifiedBytes,
      definitionsFileName: definitionsFileName,
      definitionsBytes: definitionsBytes,
      engineDisplacement: engineDisplacement,
      fuelType: fuelType,
      isTurbo: isTurbo,
      stockHp: stockHp,
    );

    final response = await http.post(
      Uri.parse('$baseUrl/api/calibration/labeling-template'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    }
    throw Exception(
      'Labeling template export failed: ${response.statusCode} ${response.body}',
    );
  }
}
