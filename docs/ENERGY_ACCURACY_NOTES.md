# Energy Metrics Accuracy and Methodology

## Current Accuracy Status

The energy metrics are **reasonably accurate estimates** based on industry-standard calculations, but they are **not precise measurements**. Here's why and how to improve them:

## Accuracy Level by Provider

### ✅ Most Accurate: Qwen (GPU-based)
- **Method**: Based on actual GPU power consumption (0.5 kW average) × processing time
- **Accuracy**: **Good** - If processing time is tracked accurately
- **Improvement**: Can be made more accurate by:
  - Tracking actual GPU power draw from Modal/cloud provider
  - Using provider-specific emission factors (e.g., Modal's grid mix)
  - Accounting for GPU type (A100 vs T4 have different power consumption)

### ⚠️ Moderate Accuracy: API Providers (GPT-4o, Gemini, Claude)
- **Method**: Token-based estimates (~0.003 kWh per 1K tokens) or default (0.002 kWh)
- **Accuracy**: **Moderate** - Estimates based on typical API usage patterns
- **Limitations**:
  - Token counts not always available for historical evaluations
  - Actual API energy varies by model version, region, and request complexity
  - Default estimate (0.002 kWh) is conservative but may not reflect actual usage
- **Improvement**: Can be made more accurate by:
  - Capturing actual token counts from API responses
  - Using provider-specific emission factors (OpenAI publishes some data)
  - Tracking model version and region

### ⚠️ Lower Accuracy: Finetuned (Mistral)
- **Method**: Estimated power (0.3 kW) × processing time
- **Accuracy**: **Moderate** - Depends on actual server configuration
- **Improvement**: Can be made more accurate by:
  - Tracking actual server power consumption
  - Knowing if it's cloud-hosted (Scope 2) or local (Scope 3)
  - Using actual grid emission factors for the server location

### ✅ Accurate: Demo Mode
- **Method**: 0 energy (no computation)
- **Accuracy**: **Perfect** - No actual computation occurs

## Emission Factors Used

### CO₂ per kWh
- **Qwen/Finetuned (Cloud)**: 0.5 kg CO₂/kWh (US grid average)
- **API Providers**: 0.4 kg CO₂/kWh (provider grid mix estimate)
- **Note**: These are conservative estimates. Actual values vary by:
  - Geographic location of data centers
  - Grid mix (renewable vs fossil fuels)
  - Time of day (grid mix changes)

### Industry Benchmarks
- **US Grid Average**: ~0.4-0.5 kg CO₂/kWh
- **OpenAI (estimated)**: ~0.4 kg CO₂/kWh (mix of renewable and grid)
- **Google Cloud**: ~0.4 kg CO₂/kWh (varies by region)
- **Modal (estimated)**: ~0.5 kg CO₂/kWh (US-based)

## Improving Accuracy

### Short-term Improvements (Easy)
1. **Capture token counts** from API responses when available
2. **Track actual processing times** (already implemented)
3. **Use provider-specific defaults** based on evaluation characteristics
   - Video evaluations: Higher energy (Qwen)
   - Text-only: Lower energy (API providers)

### Medium-term Improvements (Moderate effort)
1. **Integrate with provider APIs** for actual usage data:
   - Modal API for GPU hours and power consumption
   - OpenAI usage API for token counts and model versions
   - Google Cloud monitoring for Gemini usage
2. **Use region-specific emission factors**:
   - Track data center region
   - Apply region-specific grid mix (e.g., California vs Virginia)
3. **Account for model versions**:
   - Different model versions have different energy profiles
   - Track model version in provider_metadata

### Long-term Improvements (Significant effort)
1. **Real-time monitoring**:
   - Integrate with cloud provider monitoring APIs
   - Track actual power consumption during evaluation
2. **Lifecycle analysis**:
   - Account for model training energy (amortized)
   - Include infrastructure overhead
3. **Third-party verification**:
   - Use carbon accounting tools (e.g., Cloud Carbon Footprint)
   - Get verified emission factors from providers

## Backfilling Historical Data

Historical evaluations use **conservative estimates** because:
- Processing times are not available
- Token counts are not available
- File sizes may not be available
- Provider metadata is not available

The backfill script (`BACKFILL_ENERGY_DATA.sql`) uses:
- Default processing time estimates (30s for Qwen, 20s for Mistral)
- Default energy per evaluation for API providers (0.002 kWh)
- Conservative emission factors

**Result**: Historical data will show **lower-bound estimates** - actual energy may have been higher.

## Recommendations

### For Current Use
- ✅ **Good for**: Relative comparisons, trend analysis, awareness
- ⚠️ **Use with caution for**: Absolute carbon accounting, regulatory reporting
- ✅ **Suitable for**: Internal sustainability reporting, user education

### For Regulatory/Compliance Reporting
- Use verified emission factors from providers
- Get third-party verification
- Document methodology and assumptions
- Consider using industry-standard tools (GHG Protocol, ISO 14064)

### For Most Accurate Reporting
1. Start tracking detailed metrics for new evaluations:
   - Token counts
   - Processing times
   - Model versions
   - Regions
2. Work with providers to get actual usage data
3. Use region-specific emission factors
4. Consider third-party carbon accounting tools

## Sources and References

### Energy Estimates
- **API Providers**: Based on typical inference energy (~0.001-0.005 kWh per 1K tokens)
- **GPU Compute**: Based on typical GPU power consumption (0.3-0.5 kW)
- **Processing Times**: Based on observed evaluation times

### Emission Factors
- **US Grid Average**: EPA eGRID data (~0.4-0.5 kg CO₂/kWh)
- **Cloud Providers**: Provider sustainability reports (varies by region)
- **Conservative Approach**: Using higher estimates to avoid under-reporting

### Industry Standards
- **GHG Protocol**: Corporate Standard for carbon accounting
- **ISO 14064**: International standard for greenhouse gas accounting
- **PCAF**: Partnership for Carbon Accounting Financials (for financial institutions)

## Conclusion

The current energy metrics are **suitable for**:
- ✅ User awareness and education
- ✅ Relative comparisons (this month vs last month)
- ✅ Internal sustainability reporting
- ✅ Identifying high-energy usage patterns

The metrics should be **improved before**:
- ⚠️ Regulatory compliance reporting
- ⚠️ Public sustainability claims
- ⚠️ Carbon offset verification
- ⚠️ Third-party audits

**Recommendation**: Use current estimates for awareness and tracking, but plan to improve accuracy as the system matures and more detailed data becomes available.
