/*
 * Copyright (c) 2025, valkey-search contributors
 * All rights reserved.
 * SPDX-License-Identifier: BSD 3-Clause
 *
 */

#ifndef VALKEYSEARCH_SRC_COMMANDS_FT_CREATE_PARSER_H_
#define VALKEYSEARCH_SRC_COMMANDS_FT_CREATE_PARSER_H_

#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>

#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/strings/string_view.h"
#include "src/index_schema.pb.h"
#include "vmsdk/src/valkey_module_api/valkey_module.h"

namespace valkey_search {

struct FTCreateTagParameters {
  absl::string_view separator{","};
  bool case_sensitive{false};
};

constexpr int kDefaultInitialCap{10 * 1024};

struct FTCreateVectorParameters {
  std::optional<int> dimensions;
  data_model::DistanceMetric distance_metric{
      data_model::DistanceMetric::DISTANCE_METRIC_UNSPECIFIED};
  data_model::VectorDataType vector_data_type{
      data_model::VectorDataType::VECTOR_DATA_TYPE_UNSPECIFIED};
  int initial_cap{kDefaultInitialCap};
  absl::Status Verify() const;
  std::unique_ptr<data_model::VectorIndex> ToProto() const;
};

struct FTCreateTextParameters {
  std::string punctuation;  // Default: should we use absl here
  bool with_offsets{true};
  bool with_suffix_trie{false};
  bool no_stem{false};
  std::vector<std::string> stop_words;
  bool no_stop_words{false};
  data_model::Language language{data_model::LANGUAGE_ENGLISH}; // see if this is needed
  int min_stem_size{4};
};

struct GlobalTextDefaults {
  FTCreateTextParameters defaults;
};


constexpr int kDefaultBlockSize{1024};
constexpr int kDefaultM{16};
constexpr int kDefaultEFConstruction{200};
constexpr int kDefaultEFRuntime{10};

struct HNSWParameters : public FTCreateVectorParameters {
  // Tightly connected with internal dimensionality of the data
  // strongly affects the memory consumption
  int m{kDefaultM};
  int ef_construction{kDefaultEFConstruction};
  size_t ef_runtime{kDefaultEFRuntime};
  absl::Status Verify() const;
  std::unique_ptr<data_model::VectorIndex> ToProto() const;
};

struct FlatParameters : public FTCreateVectorParameters {
  // Block size holds the amount of vectors in a contiguous array. This is
  // useful when the index is dynamic with respect to addition and deletion.
  uint32_t block_size{kDefaultBlockSize};
  std::unique_ptr<data_model::VectorIndex> ToProto() const;
};

absl::StatusOr<data_model::IndexSchema> ParseFTCreateArgs(
    ValkeyModuleCtx *ctx, ValkeyModuleString **argv, int argc);
}  // namespace valkey_search
#endif  // VALKEYSEARCH_SRC_COMMANDS_FT_CREATE_PARSER_H_
